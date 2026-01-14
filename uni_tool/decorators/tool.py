"""
@tool decorator for registering functions as tools.

This module implements the main decorator for tool registration.
"""

from __future__ import annotations

import asyncio
import inspect
from functools import wraps
from typing import Any, Callable, List, Optional, Set, TYPE_CHECKING

from uni_tool.core.models import ToolMetadata, MiddlewareObj
from uni_tool.utils.docstring import extract_description
from uni_tool.utils.injection import create_parameters_model

if TYPE_CHECKING:
    from uni_tool.core.universe import Universe


def create_tool_decorator(
    universe: "Universe",
    *,
    name: Optional[str] = None,
    tags: Optional[Set[str]] = None,
    middlewares: Optional[List[MiddlewareObj]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Create a tool decorator bound to a specific Universe instance.

    Args:
        universe: The Universe instance to register tools with.
        name: Optional custom name for the tool.
        tags: Optional tags for filtering.
        middlewares: Optional tool-level middlewares.

    Returns:
        A decorator function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Determine the tool name
        tool_name = name or func.__name__

        # Extract description from docstring
        description = extract_description(func)

        # Check if function is async
        is_async = asyncio.iscoroutinefunction(func)

        # Create parameters model and get injected params
        parameters_model, injected_params = create_parameters_model(func, tool_name)

        # Create metadata
        metadata = ToolMetadata(
            name=tool_name,
            description=description,
            func=func,
            is_async=is_async,
            parameters_model=parameters_model,
            injected_params=injected_params,
            tags=tags or set(),
            middlewares=middlewares or [],
        )

        # Register with universe
        universe.register(metadata)

        # Return the original function unchanged
        # The wrapper is not needed as execution goes through dispatch
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Attach metadata to wrapper for introspection
        wrapper._tool_metadata = metadata  # type: ignore

        return wrapper

    return decorator
