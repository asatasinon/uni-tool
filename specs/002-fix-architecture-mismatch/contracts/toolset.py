from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .driver import BaseDriver, ToolMetadata


class ToolExpression(Protocol):
    def matches(self, meta: ToolMetadata) -> bool: ...


class ToolName:
    def __init__(self, name: str) -> None:
        self.name = name

    def matches(self, meta: ToolMetadata) -> bool:
        raise NotImplementedError


@dataclass(frozen=True)
class ToolSet:
    tools: list[ToolMetadata]
    drivers: dict[str, BaseDriver]
    expression: ToolExpression | None = None

    def render(self, driver_or_model: str) -> Any:
        """
        Render tools with explicit driver or model-based negotiation.
        """
        raise NotImplementedError

    def to_markdown(self) -> str:
        """
        Render tools to markdown documentation.
        """
        raise NotImplementedError
