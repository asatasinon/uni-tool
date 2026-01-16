from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class ModelProfile:
    name: str
    capabilities: set[str]
    protocol_hint: str | None = None


class ToolMetadata(BaseModel):
    name: str
    description: str
    tags: set[str] = Field(default_factory=set)


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict
    context: dict = Field(default_factory=dict)


class ToolResult(BaseModel):
    id: str
    result: Any | None = None
    error: str | None = None
    meta: dict = Field(default_factory=dict)


class BaseDriver(ABC):
    """
    Abstract Base Class for protocol drivers with scoring hooks.
    """

    @abstractmethod
    def can_handle(self, profile: ModelProfile) -> int:
        """
        Return 0-100 score for the given model profile.
        """
        pass

    @abstractmethod
    def can_handle_response(self, response: Any) -> int:
        """
        Return 0-100 score for the given response fingerprint.
        """
        pass

    @abstractmethod
    def render(self, tools: List[ToolMetadata]) -> Any:
        """
        Convert tools to protocol-specific schema format.
        """
        pass

    @abstractmethod
    def parse(self, response: Any) -> List[ToolCall]:
        """
        Parse the response into standardized tool calls.
        """
        pass
