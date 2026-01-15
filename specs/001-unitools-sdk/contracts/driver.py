from abc import ABC, abstractmethod
from typing import Any, List
from pydantic import BaseModel


class ToolMetadata(BaseModel):
    # Simplified for contract
    name: str
    description: str
    pass


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict
    context: dict = {}


class BaseDriver(ABC):
    """
    Abstract Base Class for LLM Protocol Drivers.
    """

    @abstractmethod
    def render(self, tools: List[ToolMetadata]) -> Any:
        """
        Convert a list of ToolMetadata into the LLM-specific schema format.
        (e.g., OpenAI JSON Schema list)
        """
        pass

    @abstractmethod
    def parse(self, response: Any) -> List[ToolCall]:
        """
        Parse the LLM response into a list of standardized ToolCalls.
        Should raise UnsupportedResponseFormatError if parsing fails.
        """
        pass
