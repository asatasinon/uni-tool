"""
Dependency injection utilities for UniTools SDK.

Handles parsing of Annotated[T, Injected(...)] type hints and runtime injection.
"""

from __future__ import annotations

import inspect
from typing import (
    Any,
    Callable,
    Dict,
    Tuple,
    Type,
    Optional,
    get_args,
    get_origin,
)
from dataclasses import dataclass

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

from uni_tool.core.errors import MissingContextKeyError
from uni_tool.utils.docstring import extract_param_descriptions


@dataclass
class Injected:
    """
    Marker for dependency-injected parameters.

    Usage:
        def my_tool(
            visible_param: str,
            user_id: Annotated[str, Injected("uid")]  # Injected from context["uid"]
        ):
            ...

    Args:
        key: The context key to inject from. If not provided, uses the parameter name.
    """

    key: Optional[str] = None

    def __repr__(self) -> str:
        return f"Injected({self.key!r})" if self.key else "Injected()"


def is_annotated_with_injected(annotation: Any) -> Tuple[bool, Optional[str]]:
    """
    Check if a type annotation contains an Injected marker.

    Args:
        annotation: The type annotation to check.

    Returns:
        A tuple of (is_injected, context_key).
        If is_injected is True, context_key is the key to inject from.
    """
    origin = get_origin(annotation)

    # Check if it's Annotated
    if origin is None:
        return False, None

    # Handle typing.Annotated
    try:
        # For Python 3.9+, Annotated has __class_getitem__
        from typing import Annotated

        if origin is Annotated:
            args = get_args(annotation)
            if len(args) >= 2:
                # Check for Injected in metadata
                for meta in args[1:]:
                    if isinstance(meta, Injected):
                        return True, meta.key
    except ImportError:
        pass

    return False, None


def parse_function_signature(
    func: Callable[..., Any],
) -> Tuple[Dict[str, Tuple[Any, Any]], Dict[str, str]]:
    """
    Parse a function's signature to extract visible parameters and injected parameters.

    Args:
        func: The function to parse.

    Returns:
        A tuple of:
        - visible_params: Dict[param_name, (type_annotation, default_value)]
        - injected_params: Dict[param_name, context_key]
    """
    sig = inspect.signature(func)
    visible_params: Dict[str, Tuple[Any, Any]] = {}
    injected_params: Dict[str, str] = {}

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        annotation = param.annotation
        default = param.default if param.default is not inspect.Parameter.empty else ...

        # Check for Injected annotation
        is_injected, context_key = is_annotated_with_injected(annotation)

        if is_injected:
            # Use the context_key if provided, otherwise use param name
            injected_params[param_name] = context_key or param_name
        else:
            # Extract the base type from Annotated if present
            origin = get_origin(annotation)
            if origin is not None:
                try:
                    from typing import Annotated

                    if origin is Annotated:
                        args = get_args(annotation)
                        annotation = args[0] if args else Any
                except ImportError:
                    pass

            visible_params[param_name] = (annotation, default)

    return visible_params, injected_params


def create_parameters_model(
    func: Callable[..., Any],
    tool_name: str,
) -> Tuple[Type[BaseModel], Dict[str, str]]:
    """
    Create a Pydantic model for the visible parameters of a function.

    This model is used to generate JSON Schema for LLM tool definitions.

    Args:
        func: The function to create a model for.
        tool_name: The name of the tool (used in model name).

    Returns:
        A tuple of (ParametersModel, injected_params_mapping).
    """
    visible_params, injected_params = parse_function_signature(func)
    param_descriptions = extract_param_descriptions(func)

    # Build field definitions for Pydantic
    field_definitions: Dict[str, Any] = {}

    for param_name, (type_hint, default) in visible_params.items():
        description = param_descriptions.get(param_name, "")

        if default is ...:
            # Required parameter
            field_definitions[param_name] = (
                type_hint,
                FieldInfo(description=description),
            )
        else:
            # Optional parameter with default
            field_definitions[param_name] = (
                type_hint,
                FieldInfo(default=default, description=description),
            )

    # Create the model
    model_name = f"{tool_name.replace('-', '_').title()}Params"
    model = create_model(model_name, **field_definitions)

    return model, injected_params


def inject_context_values(
    arguments: Dict[str, Any],
    context: Dict[str, Any],
    injected_params: Dict[str, str],
    tool_name: str,
) -> Dict[str, Any]:
    """
    Inject context values into function arguments.

    Args:
        arguments: The original arguments from LLM.
        context: The context dictionary.
        injected_params: Mapping of param_name -> context_key.
        tool_name: The tool name (for error messages).

    Returns:
        The arguments with injected values.

    Raises:
        MissingContextKeyError: If a required context key is missing.
    """
    result = dict(arguments)

    for param_name, context_key in injected_params.items():
        if context_key not in context:
            raise MissingContextKeyError(context_key, tool_name)
        result[param_name] = context[context_key]

    return result
