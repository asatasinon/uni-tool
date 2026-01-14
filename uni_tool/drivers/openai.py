"""
OpenAI driver for UniTools SDK.

Implements protocol adaptation for OpenAI's function calling API.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from uni_tool.drivers.base import BaseDriver
from uni_tool.core.models import ToolMetadata, ToolCall
from uni_tool.core.errors import UnsupportedResponseFormatError


class OpenAIDriver(BaseDriver):
    """
    Driver for OpenAI's function calling format.

    Supports both Chat Completions API tool format.
    """

    def render(self, tools: List[ToolMetadata]) -> List[Dict[str, Any]]:
        """
        Convert tools to OpenAI's function calling schema.

        Returns a list of tool definitions in OpenAI format:
        [
            {
                "type": "function",
                "function": {
                    "name": "...",
                    "description": "...",
                    "parameters": { JSON Schema }
                }
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
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema,
                },
            }
            result.append(tool_def)

        return result

    def parse(self, response: Any) -> List[ToolCall]:
        """
        Parse OpenAI response to extract tool calls.

        Supports two formats:
        1. Dict with "tool_calls" key (from ChatCompletion response)
        2. Direct list of tool call objects

        Expected tool call format:
        {
            "id": "call_xxx",
            "type": "function",
            "function": {
                "name": "tool_name",
                "arguments": '{"arg": "value"}'  # JSON string
            }
        }
        """
        tool_calls = self._extract_tool_calls(response)
        results = []

        for tc in tool_calls:
            try:
                call = self._parse_single_tool_call(tc)
                results.append(call)
            except Exception as e:
                raise UnsupportedResponseFormatError(
                    "openai",
                    f"Failed to parse tool call: {e}",
                )

        return results

    def _extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool_calls list from various response formats."""
        # Already a list of tool calls
        if isinstance(response, list):
            return response

        # Dict with tool_calls key
        if isinstance(response, dict):
            if "tool_calls" in response:
                return response["tool_calls"]

            # ChatCompletion message format
            if "choices" in response:
                choices = response["choices"]
                if choices and "message" in choices[0]:
                    message = choices[0]["message"]
                    if "tool_calls" in message:
                        return message["tool_calls"]

        raise UnsupportedResponseFormatError(
            "openai",
            f"Cannot extract tool_calls from response type: {type(response)}",
        )

    def _parse_single_tool_call(self, tc: Dict[str, Any]) -> ToolCall:
        """Parse a single tool call object."""
        call_id = tc.get("id", "")
        func_data = tc.get("function", {})
        name = func_data.get("name", "")

        # Arguments can be a JSON string or already parsed dict
        raw_args = func_data.get("arguments", "{}")
        if isinstance(raw_args, str):
            arguments = json.loads(raw_args)
        else:
            arguments = raw_args

        return ToolCall(
            id=call_id,
            name=name,
            arguments=arguments,
            context={},
        )
