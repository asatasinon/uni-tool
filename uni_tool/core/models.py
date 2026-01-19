"""
Core Pydantic models for UniTools SDK.

Defines ToolMetadata, ToolCall, ToolResult, MiddlewareObj, ModelProfile, and ToolSet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, Set, Type

from pydantic import BaseModel, Field

from uni_tool.core.expressions import ToolExpression

if TYPE_CHECKING:
    from uni_tool.drivers.base import BaseDriver


@dataclass(frozen=True)
class ModelProfile:
    """
    Profile for model capability negotiation.

    Used by ToolSet.render to select the appropriate driver.

    Attributes:
        name: Model name (e.g., "gpt-4o", "claude-3-opus").
        capabilities: Set of capability identifiers (e.g., "FC_NATIVE", "XML_FALLBACK").
        protocol_hint: Optional hint for preferred protocol.
    """

    name: str
    capabilities: Set[str] = field(default_factory=set)
    protocol_hint: Optional[str] = None


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
        """Generate uid from function/class qualname if not provided."""
        if self.uid:
            return

        uid = self._derive_uid_from_func()
        object.__setattr__(self, "uid", uid)

    def _derive_uid_from_func(self) -> str:
        """Derive a unique identifier from the middleware function."""
        # Try function's __qualname__ first
        func_qualname = getattr(self.func, "__qualname__", None)
        if func_qualname:
            return f"mw_{func_qualname}"

        # For callable class instances, use the class qualname
        func_class = type(self.func)
        if func_class.__name__ not in ("function", "method"):
            class_qualname = getattr(func_class, "__qualname__", func_class.__name__)
            return f"mw_{class_qualname}"

        # Fallback to __name__
        func_name = getattr(self.func, "__name__", "anonymous")
        return f"mw_{func_name}"


class ToolSet:
    """
    A filtered collection of tools with rendering capability.

    Returned by Universe.__getitem__ for tag filtering.
    Supports rendering to protocol-specific formats with driver negotiation.

    Attributes:
        tools: List of matching ToolMetadata.
        expression: The filter expression used to create this set.
        drivers: Available protocol drivers for rendering.
    """

    def __init__(
        self,
        tools: List[ToolMetadata],
        drivers: Dict[str, "BaseDriver"],
        expression: Optional["ToolExpression"] = None,
        model_profile_getter: Optional[Callable[[str], "ModelProfile"]] = None,
        driver_selector: Optional[Callable[["ModelProfile"], Optional["BaseDriver"]]] = None,
    ):
        self.tools = tools
        self.expression = expression
        self._drivers = drivers
        self._get_model_profile = model_profile_getter
        self._select_driver = driver_selector

    def render(self, driver_or_model: str) -> Any:
        """
        Render tools using the specified driver or model-based negotiation.

        Args:
            driver_or_model: Either a driver name (e.g., "openai") or model name (e.g., "gpt-4o").
                If a driver name, uses that driver directly.
                If a model name, negotiates the best driver using can_handle scoring.

        Returns:
            Protocol-specific tool schema (format depends on driver).

        Raises:
            ValueError: If no suitable driver is found.
        """
        # Direct driver lookup
        if driver_or_model in self._drivers:
            return self._drivers[driver_or_model].render(self.tools)

        # Model-based negotiation
        if self._get_model_profile and self._select_driver:
            profile = self._get_model_profile(driver_or_model)
            driver = self._select_driver(profile)
            if driver:
                return driver.render(self.tools)

        raise ValueError(f"No driver found for '{driver_or_model}'")

    def to_markdown(self) -> str:
        """
        Render tools to markdown documentation format.

        Returns:
            Markdown string describing all tools in this set.
        """
        if not self.tools:
            return "No tools available."

        lines = ["# Available Tools", ""]
        for tool in self.tools:
            lines.extend([f"## {tool.name}", ""])
            if tool.description:
                lines.extend([tool.description, ""])
            if tool.tags:
                tags = ", ".join(sorted(tool.tags))
                lines.extend([f"**Tags**: {tags}", ""])

        return "\n".join(lines)

    def __len__(self) -> int:
        """Get the number of tools in this set."""
        return len(self.tools)

    def __bool__(self) -> bool:
        """Check if this set has any tools."""
        return len(self.tools) > 0

    def __iter__(self):
        """Iterate over tools in this set."""
        return iter(self.tools)

    def __repr__(self) -> str:
        return f"ToolSet(tools={len(self.tools)}, expression={self.expression!r})"


# Update forward references
MiddlewareObj.model_rebuild()
