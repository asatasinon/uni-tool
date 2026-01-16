"""
Base driver interface for UniTools SDK.

Drivers handle protocol adaptation between Universe and LLM APIs.
"""

from abc import ABC, abstractmethod
from typing import Any, List

from uni_tool.core.models import ModelProfile, ToolCall, ToolMetadata


class BaseDriver(ABC):
    """
    Abstract base class for LLM protocol drivers.

    Drivers are responsible for:
    - render(): Converting ToolMetadata to LLM-specific schema format
    - parse(): Converting LLM responses to ToolCall objects
    - can_handle(): Scoring model profile compatibility (0-100)
    - can_handle_response(): Scoring response fingerprint compatibility (0-100)
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

    @abstractmethod
    def can_handle(self, profile: ModelProfile) -> int:
        """
        Score the driver's capability to handle the given model profile.

        Args:
            profile: The model profile with name and capabilities.

        Returns:
            A score from 0-100 where:
            - 0: Cannot handle this model
            - 1-50: Low confidence / fallback
            - 51-99: Good match
            - 100: Perfect match (native support)
        """
        pass

    @abstractmethod
    def can_handle_response(self, response: Any) -> int:
        """
        Score the driver's capability to parse the given response.

        Used for automatic protocol detection based on response fingerprint.

        Args:
            response: The raw LLM response to evaluate.

        Returns:
            A score from 0-100 where:
            - 0: Cannot parse this response
            - 1-50: Low confidence
            - 51-99: Good match
            - 100: Perfect match (exact format)
        """
        pass

    def _extract_text(self, response: Any) -> str:
        """
        Extract text content from a response object.

        Utility method for text-based drivers (XML, Markdown).

        Args:
            response: The raw response (string or dict).

        Returns:
            The extracted text content.
        """
        if isinstance(response, str):
            return response

        if isinstance(response, dict):
            return response.get("text", "") or response.get("content", "") or str(response)

        return str(response)
