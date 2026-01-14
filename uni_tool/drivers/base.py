"""
Base driver interface for UniTools SDK.

Drivers handle protocol adaptation between Universe and LLM APIs.
"""

from abc import ABC, abstractmethod
from typing import Any, List

from uni_tool.core.models import ToolMetadata, ToolCall


class BaseDriver(ABC):
    """
    Abstract base class for LLM protocol drivers.

    Drivers are responsible for:
    - render(): Converting ToolMetadata to LLM-specific schema format
    - parse(): Converting LLM responses to ToolCall objects
    """

    @abstractmethod
    def render(self, tools: List[ToolMetadata]) -> Any:
        """
        Convert a list of ToolMetadata into the LLM-specific schema format.

        Args:
            tools: List of tool metadata to render.

        Returns:
            The rendered schema (format depends on driver).
        """
        pass

    @abstractmethod
    def parse(self, response: Any) -> List[ToolCall]:
        """
        Parse the LLM response into a list of standardized ToolCalls.

        Args:
            response: The raw LLM response.

        Returns:
            A list of ToolCall objects.

        Raises:
            UnsupportedResponseFormatError: If parsing fails.
        """
        pass
