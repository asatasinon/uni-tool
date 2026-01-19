"""
Tool filters for UniTools SDK.

Provides common filtering expressions for tools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from uni_tool.core.expressions import ExpressionTrace, ToolExpression

if TYPE_CHECKING:
    from uni_tool.core.models import ToolCall, ToolMetadata


class Tag(ToolExpression):
    """Filter tools by tag."""

    def __init__(self, name: str):
        self.name = name

    def matches(self, metadata: "ToolMetadata") -> bool:
        return self.name in metadata.tags

    def to_dsl(self) -> str:
        """Generate DSL string for tag expression."""
        return self.name

    def diagnose(self, metadata: "ToolMetadata") -> ExpressionTrace:
        """Diagnose tag match."""
        matched = self.name in metadata.tags
        if matched:
            detail = f"Tag '{self.name}' found in {metadata.tags}"
        else:
            detail = f"Tag '{self.name}' not in {metadata.tags}"

        return ExpressionTrace(
            matched=matched,
            node="Tag",
            detail=detail,
            children=[],
        )

    def simplify(self) -> ToolExpression:
        """Atomic expressions return themselves."""
        return self

    def __repr__(self) -> str:
        return f"Tag({self.name!r})"


class Prefix(ToolExpression):
    """Filter tools by name prefix."""

    def __init__(self, prefix: str):
        self.prefix = prefix

    def matches(self, metadata: "ToolMetadata") -> bool:
        return metadata.name.startswith(self.prefix)

    def to_dsl(self) -> str:
        """Generate DSL string for prefix expression."""
        return f"prefix:{self.prefix}"

    def diagnose(self, metadata: "ToolMetadata") -> ExpressionTrace:
        """Diagnose prefix match."""
        matched = metadata.name.startswith(self.prefix)
        if matched:
            detail = f"Name '{metadata.name}' starts with '{self.prefix}'"
        else:
            detail = f"Name '{metadata.name}' does not start with '{self.prefix}'"

        return ExpressionTrace(
            matched=matched,
            node="Prefix",
            detail=detail,
            children=[],
        )

    def simplify(self) -> ToolExpression:
        """Atomic expressions return themselves."""
        return self

    def __repr__(self) -> str:
        return f"Prefix({self.prefix!r})"


class ToolName(ToolExpression):
    """
    Filter tools by exact name match.

    This provides a unified way to filter by tool name through the ToolExpression interface.
    """

    def __init__(self, name: str):
        self.name = name

    def matches(self, metadata: "ToolMetadata") -> bool:
        return metadata.name == self.name

    def matches_call(self, call: "ToolCall") -> bool:
        """Check if the tool call name matches."""
        return call.name == self.name

    def to_dsl(self) -> str:
        """Generate DSL string for name expression."""
        return f"name:{self.name}"

    def diagnose(self, metadata: "ToolMetadata") -> ExpressionTrace:
        """Diagnose name match."""
        matched = metadata.name == self.name
        if matched:
            detail = f"Name '{metadata.name}' equals '{self.name}'"
        else:
            detail = f"Name '{metadata.name}' does not equal '{self.name}'"

        return ExpressionTrace(
            matched=matched,
            node="ToolName",
            detail=detail,
            children=[],
        )

    def simplify(self) -> ToolExpression:
        """Atomic expressions return themselves."""
        return self

    def __repr__(self) -> str:
        return f"ToolName({self.name!r})"
