"""
Core Pydantic models for UniTools SDK.

Defines ToolMetadata, ToolCall, ToolResult, and MiddlewareObj.
"""

from __future__ import annotations

from typing import Any, Callable, Awaitable, Set, Dict, List, Optional, Type
from pydantic import BaseModel, Field


class ToolMetadata(BaseModel):
    """
    Describes the static properties of a registered tool.

    Attributes:
        name: Unique tool name (alphanumeric, underscores, hyphens).
        description: Tool description extracted from docstring.
        func: Reference to the original function.
        is_async: Whether the function is async.
        parameters_model: Dynamically generated Pydantic model for LLM-visible parameters.
        injected_params: Mapping of parameter name to context key for injection.
        tags: Set of tags for filtering.
        middlewares: List of tool-level middlewares.
    """

    name: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    description: str = ""
    func: Callable[..., Any] = Field(..., exclude=True)
    is_async: bool = False
    parameters_model: Optional[Type[BaseModel]] = Field(default=None, exclude=True)
    injected_params: Dict[str, str] = Field(default_factory=dict)
    tags: Set[str] = Field(default_factory=set)
    middlewares: List["MiddlewareObj"] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class ToolCall(BaseModel):
    """
    Represents an LLM-initiated tool call request.

    This object flows through the middleware pipeline.

    Attributes:
        id: Call ID (e.g., OpenAI call_id).
        name: Name of the tool to invoke.
        arguments: Raw arguments provided by LLM.
        context: Context data for dependency injection and middleware communication.
    """

    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """
    Represents the result of a tool execution.

    Attributes:
        id: Corresponding ToolCall ID.
        result: Function return value (if successful).
        error: Error message (if failed).
        meta: Additional metadata (e.g., execution time).
    """

    id: str
    result: Any = None
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """Check if the execution was successful."""
        return self.error is None


# Forward reference type for middleware function signature
NextHandler = Callable[[ToolCall], Awaitable[Any]]
MiddlewareFunc = Callable[[ToolCall, NextHandler], Awaitable[Any]]


class MiddlewareObj(BaseModel):
    """
    Encapsulates a middleware function and its configuration.

    Attributes:
        func: Middleware function with signature `async (call, next) -> result`.
        critical: Whether failure should abort the pipeline.
        scope: Tool expression for scoping (None means global).
        uid: Unique identifier for deduplication.
    """

    func: MiddlewareFunc = Field(..., exclude=True)
    critical: bool = True
    scope: Optional["ToolExpression"] = None
    uid: str = ""

    model_config = {"arbitrary_types_allowed": True}

    def model_post_init(self, __context: Any) -> None:
        """Generate uid from function name if not provided."""
        if not self.uid:
            func_name = getattr(self.func, "__name__", "anonymous")
            object.__setattr__(self, "uid", f"mw_{func_name}_{id(self.func)}")


class ToolExpression:
    """
    Base class for tool filtering expressions.

    Supports logical operations: And (&), Or (|), Not (~).
    """

    def matches(self, metadata: ToolMetadata) -> bool:
        """Check if the expression matches the given tool metadata."""
        raise NotImplementedError

    def __and__(self, other: "ToolExpression") -> "And":
        return And(self, other)

    def __or__(self, other: "ToolExpression") -> "Or":
        return Or(self, other)

    def __invert__(self) -> "Not":
        return Not(self)


class Tag(ToolExpression):
    """Filter tools by tag."""

    def __init__(self, name: str):
        self.name = name

    def matches(self, metadata: ToolMetadata) -> bool:
        return self.name in metadata.tags

    def __repr__(self) -> str:
        return f"Tag({self.name!r})"


class Prefix(ToolExpression):
    """Filter tools by name prefix."""

    def __init__(self, prefix: str):
        self.prefix = prefix

    def matches(self, metadata: ToolMetadata) -> bool:
        return metadata.name.startswith(self.prefix)

    def __repr__(self) -> str:
        return f"Prefix({self.prefix!r})"


class And(ToolExpression):
    """Logical AND of two expressions."""

    def __init__(self, left: ToolExpression, right: ToolExpression):
        self.left = left
        self.right = right

    def matches(self, metadata: ToolMetadata) -> bool:
        return self.left.matches(metadata) and self.right.matches(metadata)

    def __repr__(self) -> str:
        return f"({self.left!r} & {self.right!r})"


class Or(ToolExpression):
    """Logical OR of two expressions."""

    def __init__(self, left: ToolExpression, right: ToolExpression):
        self.left = left
        self.right = right

    def matches(self, metadata: ToolMetadata) -> bool:
        return self.left.matches(metadata) or self.right.matches(metadata)

    def __repr__(self) -> str:
        return f"({self.left!r} | {self.right!r})"


class Not(ToolExpression):
    """Logical NOT of an expression."""

    def __init__(self, expr: ToolExpression):
        self.expr = expr

    def matches(self, metadata: ToolMetadata) -> bool:
        return not self.expr.matches(metadata)

    def __repr__(self) -> str:
        return f"~{self.expr!r}"


# Update forward references
MiddlewareObj.model_rebuild()
