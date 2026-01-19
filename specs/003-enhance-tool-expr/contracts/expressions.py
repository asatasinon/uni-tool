from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, List


@dataclass(frozen=True)
class ExpressionTrace:
    matched: bool
    node: str
    detail: str
    children: List["ExpressionTrace"] = field(default_factory=list)


class ToolExpression(Protocol):
    def matches(self, metadata) -> bool: ...

    def diagnose(self, metadata) -> ExpressionTrace: ...

    def simplify(self) -> "ToolExpression": ...

    def to_dsl(self) -> str: ...


class ExpressionParser(Protocol):
    def parse(self, text: str) -> ToolExpression: ...


class ExpressionParseError(Exception):
    def __init__(self, message: str, *, line: int, column: int, context: str) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column
        self.context = context
