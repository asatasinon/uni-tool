"""
Tool filtering base expressions for UniTools SDK.

Provides composable expressions for matching tools by metadata.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uni_tool.core.models import ToolMetadata


class ToolExpression:
    """
    Base class for tool filtering expressions.

    Supports logical operations: And (&), Or (|), Not (~).
    """

    def matches(self, metadata: "ToolMetadata") -> bool:
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

    def matches(self, metadata: "ToolMetadata") -> bool:
        return self.left.matches(metadata) and self.right.matches(metadata)

    def __repr__(self) -> str:
        return f"({self.left!r} & {self.right!r})"


class Or(ToolExpression):
    """Logical OR of two expressions."""

    def __init__(self, left: ToolExpression, right: ToolExpression):
        self.left = left
        self.right = right

    def matches(self, metadata: "ToolMetadata") -> bool:
        return self.left.matches(metadata) or self.right.matches(metadata)

    def __repr__(self) -> str:
        return f"({self.left!r} | {self.right!r})"


class Not(ToolExpression):
    """Logical NOT of an expression."""

    def __init__(self, expr: ToolExpression):
        self.expr = expr

    def matches(self, metadata: "ToolMetadata") -> bool:
        return not self.expr.matches(metadata)

    def __repr__(self) -> str:
        return f"~{self.expr!r}"
