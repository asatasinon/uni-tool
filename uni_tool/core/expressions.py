"""
Tool filtering base expressions for UniTools SDK.

Provides composable expressions for matching tools by metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from uni_tool.core.models import ToolMetadata


@dataclass(frozen=True)
class ExpressionTrace:
    """
    Diagnostic trace node for expression evaluation.

    Captures the evaluation path and explains match/failure reasons.
    """

    matched: bool
    node: str
    detail: str
    children: List["ExpressionTrace"] = field(default_factory=list)


class ToolExpression:
    """
    Base class for tool filtering expressions.

    Supports logical operations: And (&), Or (|), Not (~).
    Provides DSL serialization, diagnostics, and simplification.
    """

    def matches(self, metadata: "ToolMetadata") -> bool:
        """Check if the expression matches the given tool metadata."""
        raise NotImplementedError

    def to_dsl(self) -> str:
        """
        Generate a DSL string representation that can be parsed back.

        Returns:
            A DSL string that represents this expression.
        """
        raise NotImplementedError

    def diagnose(self, metadata: "ToolMetadata") -> ExpressionTrace:
        """
        Generate a diagnostic trace explaining the match result.

        Args:
            metadata: The tool metadata to evaluate against.

        Returns:
            An ExpressionTrace with match result and explanation.
        """
        raise NotImplementedError

    def simplify(self) -> "ToolExpression":
        """
        Return a simplified version of this expression.

        Applies rules like deduplication, flattening, and double-negation elimination.

        Returns:
            A semantically equivalent but potentially simpler expression.
        """
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

    def to_dsl(self) -> str:
        """Generate DSL string with proper precedence handling."""
        left_dsl = self.left.to_dsl()
        right_dsl = self.right.to_dsl()

        # Wrap Or children in parentheses (lower precedence)
        if isinstance(self.left, Or):
            left_dsl = f"({left_dsl})"
        if isinstance(self.right, Or):
            right_dsl = f"({right_dsl})"

        return f"{left_dsl} & {right_dsl}"

    def diagnose(self, metadata: "ToolMetadata") -> ExpressionTrace:
        """Diagnose AND expression by evaluating both children."""
        left_trace = self.left.diagnose(metadata)
        right_trace = self.right.diagnose(metadata)
        matched = left_trace.matched and right_trace.matched

        if matched:
            detail = "Both conditions matched"
        elif not left_trace.matched and not right_trace.matched:
            detail = "Both conditions failed"
        elif not left_trace.matched:
            detail = "Left condition failed"
        else:
            detail = "Right condition failed"

        return ExpressionTrace(
            matched=matched,
            node="And",
            detail=detail,
            children=[left_trace, right_trace],
        )

    def simplify(self) -> ToolExpression:
        """Simplify AND expression."""
        left = self.left.simplify()
        right = self.right.simplify()

        # Flatten nested And
        operands: List[ToolExpression] = []
        _flatten_and(left, operands)
        _flatten_and(right, operands)

        # Remove duplicates while preserving order
        seen: List[str] = []
        unique: List[ToolExpression] = []
        for op in operands:
            dsl = op.to_dsl()
            if dsl not in seen:
                seen.append(dsl)
                unique.append(op)

        if len(unique) == 1:
            return unique[0]

        # Rebuild And chain
        result = unique[0]
        for op in unique[1:]:
            result = And(result, op)
        return result

    def __repr__(self) -> str:
        return f"({self.left!r} & {self.right!r})"


class Or(ToolExpression):
    """Logical OR of two expressions."""

    def __init__(self, left: ToolExpression, right: ToolExpression):
        self.left = left
        self.right = right

    def matches(self, metadata: "ToolMetadata") -> bool:
        return self.left.matches(metadata) or self.right.matches(metadata)

    def to_dsl(self) -> str:
        """Generate DSL string (no parentheses needed - lowest precedence)."""
        return f"{self.left.to_dsl()} | {self.right.to_dsl()}"

    def diagnose(self, metadata: "ToolMetadata") -> ExpressionTrace:
        """Diagnose OR expression by evaluating both children."""
        left_trace = self.left.diagnose(metadata)
        right_trace = self.right.diagnose(metadata)
        matched = left_trace.matched or right_trace.matched

        if matched:
            if left_trace.matched and right_trace.matched:
                detail = "Both conditions matched"
            elif left_trace.matched:
                detail = "Left condition matched"
            else:
                detail = "Right condition matched"
        else:
            detail = "Neither condition matched"

        return ExpressionTrace(
            matched=matched,
            node="Or",
            detail=detail,
            children=[left_trace, right_trace],
        )

    def simplify(self) -> ToolExpression:
        """Simplify OR expression."""
        left = self.left.simplify()
        right = self.right.simplify()

        # Flatten nested Or
        operands: List[ToolExpression] = []
        _flatten_or(left, operands)
        _flatten_or(right, operands)

        # Remove duplicates while preserving order
        seen: List[str] = []
        unique: List[ToolExpression] = []
        for op in operands:
            dsl = op.to_dsl()
            if dsl not in seen:
                seen.append(dsl)
                unique.append(op)

        if len(unique) == 1:
            return unique[0]

        # Rebuild Or chain
        result = unique[0]
        for op in unique[1:]:
            result = Or(result, op)
        return result

    def __repr__(self) -> str:
        return f"({self.left!r} | {self.right!r})"


class Not(ToolExpression):
    """Logical NOT of an expression."""

    def __init__(self, expr: ToolExpression):
        self.expr = expr

    def matches(self, metadata: "ToolMetadata") -> bool:
        return not self.expr.matches(metadata)

    def to_dsl(self) -> str:
        """Generate DSL string with proper precedence handling."""
        inner_dsl = self.expr.to_dsl()

        # Wrap binary operators in parentheses
        if isinstance(self.expr, (And, Or)):
            return f"~({inner_dsl})"
        return f"~{inner_dsl}"

    def diagnose(self, metadata: "ToolMetadata") -> ExpressionTrace:
        """Diagnose NOT expression by inverting child result."""
        child_trace = self.expr.diagnose(metadata)
        matched = not child_trace.matched

        if matched:
            detail = "Negation succeeded (inner condition failed)"
        else:
            detail = "Negation failed (inner condition matched)"

        return ExpressionTrace(
            matched=matched,
            node="Not",
            detail=detail,
            children=[child_trace],
        )

    def simplify(self) -> ToolExpression:
        """Simplify NOT expression with double negation elimination."""
        inner = self.expr.simplify()

        # Double negation elimination: ~~A -> A
        if isinstance(inner, Not):
            return inner.expr.simplify()

        return Not(inner)

    def __repr__(self) -> str:
        return f"~{self.expr!r}"


def _flatten_and(expr: ToolExpression, operands: List[ToolExpression]) -> None:
    """Flatten nested And expressions into a list of operands."""
    if isinstance(expr, And):
        _flatten_and(expr.left, operands)
        _flatten_and(expr.right, operands)
    else:
        operands.append(expr)


def _flatten_or(expr: ToolExpression, operands: List[ToolExpression]) -> None:
    """Flatten nested Or expressions into a list of operands."""
    if isinstance(expr, Or):
        _flatten_or(expr.left, operands)
        _flatten_or(expr.right, operands)
    else:
        operands.append(expr)
