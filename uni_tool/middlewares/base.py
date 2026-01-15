"""
Middleware base definitions for UniTools SDK.

Implements the "Onion Model" middleware pattern.
"""

from __future__ import annotations

from typing import Any, Protocol, TYPE_CHECKING
import logging

from uni_tool.core.models import ToolCall, MiddlewareObj, NextHandler

if TYPE_CHECKING:
    from uni_tool.core.models import ToolMetadata

logger = logging.getLogger(__name__)


class MiddlewareProtocol(Protocol):
    """
    Protocol for middleware functions.

    Middleware follows the "Onion Model":
    - Receives the call and a next_handler
    - Can modify the call before passing to next_handler
    - Can modify the result after next_handler returns
    - Can short-circuit by not calling next_handler
    """

    async def __call__(self, call: ToolCall, next_handler: NextHandler) -> Any:
        """
        Process the tool call through the middleware.

        Args:
            call: The current tool call object (with context).
            next_handler: The next function in the middleware pipeline.

        Returns:
            The result of the execution (possibly modified).
        """
        ...


def wrap_middleware(
    middleware: MiddlewareObj,
    next_handler: NextHandler,
) -> NextHandler:
    """
    Wrap a middleware around a next_handler, creating a new handler.

    This implements exception isolation based on the `critical` flag:
    - critical=True: Exceptions propagate and abort the pipeline
    - critical=False: Exceptions are logged, and next_handler is called

    Args:
        middleware: The middleware object to wrap.
        next_handler: The next handler in the chain.

    Returns:
        A new handler that wraps the middleware logic.
    """

    async def wrapped(call: ToolCall) -> Any:
        try:
            return await middleware.func(call, next_handler)
        except Exception as e:
            if middleware.critical:
                # Critical middleware: propagate the exception
                raise
            else:
                # Non-critical middleware: log and skip
                middleware_name = getattr(middleware.func, "__name__", "anonymous")
                logger.warning(
                    f"Non-critical middleware '{middleware_name}' failed: {e}. Continuing pipeline execution."
                )
                return await next_handler(call)

    return wrapped


def build_middleware_chain(
    middlewares: list[MiddlewareObj],
    final_handler: NextHandler,
) -> NextHandler:
    """
    Build a middleware chain from a list of middlewares.

    The chain is built in reverse order so that the first middleware
    in the list is executed first (outermost layer of the onion).

    Args:
        middlewares: List of middleware objects, in execution order.
        final_handler: The final handler (actual tool execution).

    Returns:
        A handler that passes through all middlewares.
    """
    handler = final_handler

    # Build chain in reverse order
    for middleware in reversed(middlewares):
        handler = wrap_middleware(middleware, handler)

    return handler


def filter_middlewares_for_tool(
    middlewares: list[MiddlewareObj],
    metadata: "ToolMetadata",
) -> list[MiddlewareObj]:
    """
    Filter middlewares that apply to a specific tool.

    Args:
        middlewares: List of all middlewares.
        metadata: The tool metadata.

    Returns:
        List of middlewares that match the tool.
    """
    return [mw for mw in middlewares if mw.scope is None or mw.scope.matches(metadata)]


def deduplicate_middlewares(
    middlewares: list[MiddlewareObj],
) -> list[MiddlewareObj]:
    """
    Deduplicate middlewares by uid.

    Later middlewares with the same uid override earlier ones.

    Args:
        middlewares: List of middlewares (may contain duplicates).

    Returns:
        Deduplicated list preserving order of last occurrence.
    """
    seen: dict[str, int] = {}
    result: list[MiddlewareObj] = []

    for mw in middlewares:
        if mw.uid and mw.uid in seen:
            # Replace the previous occurrence
            result[seen[mw.uid]] = mw
        else:
            if mw.uid:
                seen[mw.uid] = len(result)
            result.append(mw)

    return result
