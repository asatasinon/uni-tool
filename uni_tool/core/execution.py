"""
Execution pipeline for UniTools SDK.

This module implements the core dispatch and execution logic with middleware support.
"""

from __future__ import annotations

import asyncio
import copy
import time
from typing import Any, List, TYPE_CHECKING

from uni_tool.core.models import ToolCall, ToolResult, MiddlewareObj
from uni_tool.core.errors import (
    ToolNotFoundError,
    MissingContextKeyError,
)
from uni_tool.utils.injection import inject_context_values
from uni_tool.middlewares.base import (
    build_middleware_chain,
    filter_middlewares_for_tool,
    deduplicate_middlewares,
    NextHandler,
)

if TYPE_CHECKING:
    from uni_tool.core.universe import Universe


def create_final_handler(
    universe: "Universe",
    metadata: Any,
) -> NextHandler:
    """
    Create the final handler that executes the actual tool function.

    Args:
        universe: The Universe instance.
        metadata: The tool metadata.

    Returns:
        An async handler function.
    """

    async def final_handler(call: ToolCall) -> Any:
        # First, validate LLM-provided arguments with Pydantic model
        if metadata.parameters_model:
            validated = metadata.parameters_model(**call.arguments)
            validated_args = validated.model_dump()
        else:
            validated_args = dict(call.arguments)

        # Then inject context values (these are NOT in the Pydantic model)
        arguments = inject_context_values(
            validated_args,
            call.context,
            metadata.injected_params,
            call.name,
        )

        # Execute the function
        if metadata.is_async:
            return await metadata.func(**arguments)
        else:
            # Run sync function in thread pool to avoid blocking
            return await asyncio.to_thread(metadata.func, **arguments)

    return final_handler


def assemble_middlewares(
    universe: "Universe",
    metadata: Any,
) -> List[MiddlewareObj]:
    """
    Assemble all applicable middlewares for a tool.

    Order: Global -> Scoped -> Local (tool-level)

    Args:
        universe: The Universe instance.
        metadata: The tool metadata.

    Returns:
        A deduplicated list of middlewares in execution order.
    """
    # 1. Global middlewares (always apply)
    global_mws = list(universe._global_middlewares)

    # 2. Scoped middlewares (filter by expression)
    scoped_mws = filter_middlewares_for_tool(
        universe._scoped_middlewares,
        metadata,
    )

    # 3. Local middlewares (tool-level)
    local_mws = list(metadata.middlewares)

    # Combine and deduplicate
    all_mws = global_mws + scoped_mws + local_mws
    return deduplicate_middlewares(all_mws)


async def execute_single_tool(
    universe: "Universe",
    call: ToolCall,
) -> ToolResult:
    """
    Execute a single tool call through the middleware pipeline.

    Pipeline order: Global -> Scoped -> Local -> Execution

    Args:
        universe: The Universe instance.
        call: The tool call to execute.

    Returns:
        A ToolResult with the execution result or error.
    """
    start_time = time.perf_counter()

    try:
        # Get tool metadata
        metadata = universe.get(call.name)
        if metadata is None:
            raise ToolNotFoundError(call.name)

        # Assemble middlewares
        middlewares = assemble_middlewares(universe, metadata)

        # Create the final handler (actual execution)
        final_handler = create_final_handler(universe, metadata)

        # Build middleware chain
        chain = build_middleware_chain(middlewares, final_handler)

        # Execute through the chain
        result = await chain(call)

        elapsed = time.perf_counter() - start_time

        return ToolResult(
            id=call.id,
            result=result,
            error=None,
            meta={"elapsed_ms": round(elapsed * 1000, 2)},
        )

    except MissingContextKeyError as e:
        return ToolResult(
            id=call.id,
            result=None,
            error=str(e),
            meta={"error_type": "MissingContextKeyError"},
        )

    except ToolNotFoundError as e:
        return ToolResult(
            id=call.id,
            result=None,
            error=str(e),
            meta={"error_type": "ToolNotFoundError"},
        )

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        return ToolResult(
            id=call.id,
            result=None,
            error=str(e),
            meta={
                "elapsed_ms": round(elapsed * 1000, 2),
                "error_type": type(e).__name__,
            },
        )


def _isolate_context(call: ToolCall) -> ToolCall:
    """
    Create a copy of the ToolCall with an isolated context.

    This ensures that parallel executions do not cross-contaminate context data.

    Args:
        call: The original ToolCall.

    Returns:
        A new ToolCall with a deep-copied context.
    """
    return ToolCall(
        id=call.id,
        name=call.name,
        arguments=call.arguments,  # Arguments are read-only, no need to copy
        context=copy.deepcopy(call.context),
    )


async def execute_tool_calls(
    universe: "Universe",
    calls: List[ToolCall],
) -> List[ToolResult]:
    """
    Execute multiple tool calls in parallel.

    Uses asyncio.gather for parallel execution while maintaining result order
    matching the input call order. Each call receives an isolated context copy.

    Args:
        universe: The Universe instance.
        calls: List of tool calls to execute.

    Returns:
        A list of ToolResult objects in the same order as calls.
    """
    if not calls:
        return []

    # Create isolated copies of each call to prevent context cross-contamination
    isolated_calls = [_isolate_context(call) for call in calls]

    # Execute all calls in parallel
    results = await asyncio.gather(
        *[execute_single_tool(universe, call) for call in isolated_calls],
        return_exceptions=False,  # Let exceptions propagate through ToolResult.error
    )

    return list(results)
