"""
OpenAI driver for UniTools SDK.

Implements protocol adaptation for OpenAI's function calling API.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from uni_tool.drivers.base import BaseDriver
from uni_tool.core.models import ToolMetadata, ToolCall, ModelProfile
from uni_tool.core.errors import UnsupportedResponseFormatError


class OpenAIDriver(BaseDriver):
    """
    Driver for OpenAI's function calling format.

    Supports both Chat Completions API tool format.
    """

    # OpenAI-compatible model prefixes
    SUPPORTED_MODEL_PREFIXES = ("gpt-", "o1-", "o3-")

    def can_handle(self, profile: ModelProfile) -> int:
        """
        Score capability to handle the model profile.

        Returns 100 for OpenAI models, 0 otherwise.
        """
        model_name = profile.name.lower()

        # Native support for OpenAI models
        for prefix in self.SUPPORTED_MODEL_PREFIXES:
            if model_name.startswith(prefix):
                return 100

        # Check for FC_NATIVE capability
        if "FC_NATIVE" in profile.capabilities:
            return 50

        return 0

    def can_handle_response(self, response: Any) -> int:
        """
        Score capability to parse the response based on OpenAI fingerprint.

        Returns 100 for responses with OpenAI tool_calls structure.
        """
        try:
            if self._is_openai_tool_calls_list(response):
                return 100
            if isinstance(response, dict) and self._has_openai_tool_calls(response):
                return 100
            return 0
        except Exception:
            return 0

    def _is_openai_tool_calls_list(self, response: Any) -> bool:
        """Check if response is a direct list of OpenAI tool calls."""
        if not isinstance(response, list) or not response:
            return False
        first = response[0]
        return isinstance(first, dict) and first.get("type") == "function" and "name" in first.get("function", {})

    def _has_openai_tool_calls(self, response: dict) -> bool:
        """Check if dict response contains OpenAI tool_calls."""
        # Direct tool_calls key
        if "tool_calls" in response:
            tool_calls = response["tool_calls"]
            if isinstance(tool_calls, list) and tool_calls:
                first = tool_calls[0]
                if isinstance(first, dict) and first.get("type") == "function":
                    return True

        # ChatCompletion format: choices[0].message.tool_calls
        choices = response.get("choices", [])
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message", {})
            if "tool_calls" in message:
                return True

        return False

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
