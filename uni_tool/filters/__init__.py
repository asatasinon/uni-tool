"""
Tool filters for UniTools SDK.

Provides common filtering expressions for tools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from uni_tool.core.expressions import ToolExpression

if TYPE_CHECKING:
    from uni_tool.core.models import ToolCall, ToolMetadata


class Tag(ToolExpression):
    """Filter tools by tag."""

    def __init__(self, name: str):
        self.name = name

    def matches(self, metadata: "ToolMetadata") -> bool:
        return self.name in metadata.tags

    def __repr__(self) -> str:
        return f"Tag({self.name!r})"


class Prefix(ToolExpression):
    """Filter tools by name prefix."""

    def __init__(self, prefix: str):
        self.prefix = prefix

    def matches(self, metadata: "ToolMetadata") -> bool:
        return metadata.name.startswith(self.prefix)

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

    def __repr__(self) -> str:
        return f"ToolName({self.name!r})"
