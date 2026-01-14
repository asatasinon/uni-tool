"""
@bind decorator for registering class methods as tools.

This module implements the class decorator for bulk tool registration.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, Optional, Set, TYPE_CHECKING

from uni_tool.core.models import ToolMetadata
from uni_tool.utils.docstring import extract_description
from uni_tool.utils.injection import create_parameters_model

if TYPE_CHECKING:
    from uni_tool.core.universe import Universe


def create_bind_decorator(
    universe: "Universe",
    *,
    prefix: Optional[str] = None,
    tags: Optional[Set[str]] = None,
) -> Callable[[type], type]:
    """
    Create a bind decorator bound to a specific Universe instance.

    The @bind decorator registers all public methods of a class as tools.
    Methods starting with underscore are skipped.

    Args:
        universe: The Universe instance to register tools with.
        prefix: Optional prefix for tool names (e.g., "math_" + "add" -> "math_add").
        tags: Optional tags applied to all registered methods.

    Returns:
        A class decorator.
    """

    def decorator(cls: type) -> type:
        # Create an instance to bind methods
        instance = cls()

        # Iterate over all methods
        for method_name in dir(instance):
            # Skip private and magic methods
            if method_name.startswith("_"):
                continue

            method = getattr(instance, method_name)

            # Skip non-callables
            if not callable(method):
                continue

            # Skip class/static methods that aren't bound
            if not inspect.ismethod(method):
                continue

            # Build tool name
            tool_name = f"{prefix}{method_name}" if prefix else method_name

            # Extract description
            description = extract_description(method)

            # Check if async
            is_async = asyncio.iscoroutinefunction(method)

            # Create parameters model
            parameters_model, injected_params = create_parameters_model(
                method, tool_name
            )

            # Create metadata
            metadata = ToolMetadata(
                name=tool_name,
                description=description,
                func=method,
                is_async=is_async,
                parameters_model=parameters_model,
                injected_params=injected_params,
                tags=tags or set(),
                middlewares=[],
            )

            # Register with universe
            universe.register(metadata)

        # Store reference to instance for lifecycle management
        cls._bound_instance = instance  # type: ignore

        return cls

    return decorator
