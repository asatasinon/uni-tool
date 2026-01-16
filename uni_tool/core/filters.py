"""
Tool filtering expressions for UniTools SDK.

Provides composable expressions for matching tools by metadata.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from uni_tool.core.models import ToolMetadata

if TYPE_CHECKING:
    from uni_tool.core.models import ToolCall


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


class ToolName(ToolExpression):
    """
    Filter tools by exact name match.

    This provides a unified way to filter by tool name through the ToolExpression interface.
    """

    def __init__(self, name: str):
        self.name = name

    def matches(self, metadata: ToolMetadata) -> bool:
        return metadata.name == self.name

    def matches_call(self, call: "ToolCall") -> bool:
        """Check if the tool call name matches."""
        return call.name == self.name

    def __repr__(self) -> str:
        return f"ToolName({self.name!r})"


ToolFilter = ToolExpression | None
