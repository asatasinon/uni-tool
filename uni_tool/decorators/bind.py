"""
@bind decorator for registering class methods as tools.

This module implements the class decorator for bulk tool registration.
"""

from __future__ import annotations

import inspect
from typing import Callable, List, Optional, Set, TYPE_CHECKING

from uni_tool.core.models import ToolMetadata, MiddlewareObj
from uni_tool.utils.docstring import extract_description
from uni_tool.utils.injection import create_parameters_model

if TYPE_CHECKING:
    from uni_tool.core.universe import Universe


def create_bind_decorator(
    universe: "Universe",
    *,
    prefix: Optional[str] = None,
    tags: Optional[Set[str]] = None,
    exclude: Optional[List[str]] = None,
    middlewares: Optional[List[MiddlewareObj]] = None,
) -> Callable[[type], type]:
    """
    Create a bind decorator bound to a specific Universe instance.

    The @bind decorator registers all public methods of a class as tools.
    Methods starting with underscore are skipped.

    Args:
        universe: The Universe instance to register tools with.
        prefix: Optional prefix for tool names (e.g., "math_" + "add" -> "math_add").
        tags: Optional tags applied to all registered methods.
        exclude: Optional list of method names to exclude from registration.
        middlewares: Optional list of middlewares to apply to all registered methods.

    Returns:
        A class decorator.
    """
    exclude_set = set(exclude) if exclude else set()
    middleware_list = list(middlewares) if middlewares else []

    def decorator(cls: type) -> type:
        instance = cls()

        for method_name in dir(instance):
            if method_name.startswith("_"):
                continue

            # Skip excluded methods
            if method_name in exclude_set:
                continue

            method = getattr(instance, method_name)

            # Skip non-callables and non-bound methods
            if not callable(method) or not inspect.ismethod(method):
                continue

            tool_name = f"{prefix}{method_name}" if prefix else method_name
            parameters_model, injected_params = create_parameters_model(method, tool_name)

            metadata = ToolMetadata(
                name=tool_name,
                description=extract_description(method),
                func=method,
                is_async=inspect.iscoroutinefunction(method),
                parameters_model=parameters_model,
                injected_params=injected_params,
                tags=tags or set(),
                middlewares=middleware_list,
            )
            universe.register(metadata)

        # Store reference to instance for lifecycle management
        cls._bound_instance = instance  # type: ignore
        return cls

    return decorator
