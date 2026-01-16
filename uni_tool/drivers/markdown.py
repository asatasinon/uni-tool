"""
Markdown driver for UniTools SDK.

Implements protocol adaptation for Markdown-based tool calling format.
"""

from __future__ import annotations

import re
import json
from typing import Any, List

from uni_tool.drivers.base import BaseDriver
from uni_tool.core.models import ToolMetadata, ToolCall, ModelProfile
from uni_tool.core.errors import UnsupportedResponseFormatError


class MarkdownDriver(BaseDriver):
    """
    Driver for Markdown-based tool calling format.

    Supports tool calls embedded in markdown code blocks:
    ```tool_call
    {
        "name": "tool_name",
        "arguments": {"arg": "value"}
    }
    ```
    """

    # Markdown tool call pattern
    TOOL_CALL_PATTERN = re.compile(
        r"```(?:tool_call|json:tool_call|tool)\s*\n(.*?)```",
        re.DOTALL | re.IGNORECASE,
    )

    # Alternative: Action format (allows leading whitespace/newlines)
    ACTION_PATTERN = re.compile(
        r"Action:\s*(\w+)\s*\n\s*Action Input:\s*(\{.*?\}|\[.*?\])",
        re.DOTALL | re.MULTILINE,
    )

    def can_handle(self, profile: ModelProfile) -> int:
        """
        Score capability to handle the model profile.

        Returns 20 as low-priority fallback (markdown is universal).
        """
        # Markdown is a universal fallback with low priority
        return 20

    def can_handle_response(self, response: Any) -> int:
        """
        Score capability to parse the response based on Markdown fingerprint.

        Returns 100 for responses containing tool_call code blocks or Action format.
        """
        try:
            text = self._extract_text(response)

            # Check for tool_call code blocks
            if self.TOOL_CALL_PATTERN.search(text):
                return 100

            # Check for Action/Action Input format
            if self.ACTION_PATTERN.search(text):
                return 80

            return 0
        except Exception:
            return 0

    def render(self, tools: List[ToolMetadata]) -> str:
        """
        Convert tools to Markdown documentation format.

        Returns Markdown describing available tools for prompt injection.
        """
        lines = ["# Available Tools", ""]

        for tool in tools:
            lines.append(f"## {tool.name}")
            lines.append("")
            lines.append(tool.description or "No description available.")
            lines.append("")

            # Generate parameters from Pydantic model
            if tool.parameters_model:
                schema = tool.parameters_model.model_json_schema()
                properties = schema.get("properties", {})
                required = schema.get("required", [])

                if properties:
                    lines.append("### Parameters")
                    lines.append("")
                    lines.append("| Name | Type | Required | Description |")
                    lines.append("|------|------|----------|-------------|")

                    for param_name, param_info in properties.items():
                        param_type = param_info.get("type", "string")
                        param_desc = param_info.get("description", "")
                        is_required = "Yes" if param_name in required else "No"
                        lines.append(f"| {param_name} | {param_type} | {is_required} | {param_desc} |")

                    lines.append("")

            # Usage example
            lines.append("### Usage")
            lines.append("")
            lines.append("```tool_call")
            example = {"name": tool.name, "arguments": {}}
            lines.append(json.dumps(example, indent=2))
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def parse(self, response: Any) -> List[ToolCall]:
        """
        Parse Markdown response to extract tool calls.

        Supports two formats:
        1. Code block format: ```tool_call { "name": "...", "arguments": {...} } ```
        2. Action format: Action: tool_name \n Action Input: {...}
        """
        text = self._extract_text(response)
        results = []

        # Try code block format first
        code_matches = self.TOOL_CALL_PATTERN.findall(text)
        for i, match in enumerate(code_matches):
            try:
                call = self._parse_code_block(match.strip(), i)
                results.append(call)
            except Exception as e:
                raise UnsupportedResponseFormatError(
                    "markdown",
                    f"Failed to parse tool_call code block: {e}",
                )

        # Try Action format if no code blocks found
        if not results:
            action_matches = self.ACTION_PATTERN.findall(text)
            for i, (action_name, action_input) in enumerate(action_matches):
                try:
                    call = self._parse_action_format(action_name, action_input, i)
                    results.append(call)
                except Exception as e:
                    raise UnsupportedResponseFormatError(
                        "markdown",
                        f"Failed to parse Action format: {e}",
                    )

        return results

    def _parse_code_block(self, content: str, index: int) -> ToolCall:
        """Parse a tool_call code block."""
        data = json.loads(content)

        name = data.get("name", "")
        arguments = data.get("arguments", {})
        call_id = data.get("id", f"md_call_{index}")

        return ToolCall(
            id=call_id,
            name=name,
            arguments=arguments,
            context={},
        )

    def _parse_action_format(self, action_name: str, action_input: str, index: int) -> ToolCall:
        """Parse Action/Action Input format."""
        arguments = json.loads(action_input)

        return ToolCall(
            id=f"action_call_{index}",
            name=action_name.strip(),
            arguments=arguments,
            context={},
        )
