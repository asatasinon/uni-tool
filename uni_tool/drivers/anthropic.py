"""
Anthropic driver for UniTools SDK.

Implements protocol adaptation for Anthropic's tool use API.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from uni_tool.drivers.base import BaseDriver
from uni_tool.core.models import ToolMetadata, ToolCall, ModelProfile
from uni_tool.core.errors import UnsupportedResponseFormatError


class AnthropicDriver(BaseDriver):
    """
    Driver for Anthropic's tool use format.

    Supports Claude 3.x tool use API format.
    """

    # Anthropic-compatible model prefixes
    SUPPORTED_MODEL_PREFIXES = ("claude-",)

    def can_handle(self, profile: ModelProfile) -> int:
        """
        Score capability to handle the model profile.

        Returns 100 for Anthropic models, 0 otherwise.
        """
        model_name = profile.name.lower()

        # Native support for Claude models
        for prefix in self.SUPPORTED_MODEL_PREFIXES:
            if model_name.startswith(prefix):
                return 100

        # Check for FC_NATIVE capability with XML_FALLBACK hint
        if "FC_NATIVE" in profile.capabilities and "XML_FALLBACK" in profile.capabilities:
            return 60

        return 0

    def can_handle_response(self, response: Any) -> int:
        """
        Score capability to parse the response based on Anthropic fingerprint.

        Returns 100 for responses with Anthropic tool_use structure.
        """
        try:
            if self._has_tool_use_block(response):
                return 100
            return 0
        except Exception:
            return 0

    def _has_tool_use_block(self, response: Any) -> bool:
        """Check if response contains Anthropic tool_use blocks."""
        if isinstance(response, dict):
            # Direct tool_use type
            if response.get("type") == "tool_use":
                return True
            # Content array with tool_use blocks
            content = response.get("content", [])
            if isinstance(content, list):
                return any(isinstance(block, dict) and block.get("type") == "tool_use" for block in content)

        # List of tool_use blocks
        if isinstance(response, list) and response:
            first = response[0]
            return isinstance(first, dict) and first.get("type") == "tool_use"

        return False

    def render(self, tools: List[ToolMetadata]) -> List[Dict[str, Any]]:
        """
        Convert tools to Anthropic's tool use schema.

        Returns a list of tool definitions in Anthropic format:
        [
            {
                "name": "...",
                "description": "...",
                "input_schema": { JSON Schema }
            }
        ]
        """
        result = []

        for tool in tools:
            # Generate JSON Schema from Pydantic model
            if tool.parameters_model:
                schema = tool.parameters_model.model_json_schema()
                # Remove Pydantic-specific fields
                schema.pop("title", None)
            else:
                schema = {"type": "object", "properties": {}}

            tool_def = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": schema,
            }
            result.append(tool_def)

        return result

    def parse(self, response: Any) -> List[ToolCall]:
        """
        Parse Anthropic response to extract tool calls.

        Supports two formats:
        1. Dict with "content" array containing tool_use blocks
        2. Direct list of tool_use blocks

        Expected tool_use format:
        {
            "type": "tool_use",
            "id": "toolu_xxx",
            "name": "tool_name",
            "input": {"arg": "value"}
        }
        """
        tool_use_blocks = self._extract_tool_use_blocks(response)
        results = []

        for block in tool_use_blocks:
            try:
                call = self._parse_single_tool_use(block)
                results.append(call)
            except Exception as e:
                raise UnsupportedResponseFormatError(
                    "anthropic",
                    f"Failed to parse tool_use block: {e}",
                )

        return results

    def _extract_tool_use_blocks(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool_use blocks from various response formats."""
        # Already a list of blocks
        if isinstance(response, list):
            return [b for b in response if isinstance(b, dict) and b.get("type") == "tool_use"]

        # Dict with content array
        if isinstance(response, dict):
            content = response.get("content", [])
            if isinstance(content, list):
                return [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]

            # Single tool_use block
            if response.get("type") == "tool_use":
                return [response]

        raise UnsupportedResponseFormatError(
            "anthropic",
            f"Cannot extract tool_use blocks from response type: {type(response)}",
        )

    def _parse_single_tool_use(self, block: Dict[str, Any]) -> ToolCall:
        """Parse a single tool_use block."""
        call_id = block.get("id", "")
        name = block.get("name", "")

        # Input can be a dict or JSON string
        raw_input = block.get("input", {})
        if isinstance(raw_input, str):
            arguments = json.loads(raw_input)
        else:
            arguments = raw_input

        return ToolCall(
            id=call_id,
            name=name,
            arguments=arguments,
            context={},
        )
