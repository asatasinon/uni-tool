"""
Gemini driver for UniTools SDK.

Implements protocol adaptation for Gemini function calling format.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from uni_tool.core.errors import UnsupportedResponseFormatError
from uni_tool.core.models import ModelProfile, ToolCall, ToolMetadata
from uni_tool.drivers.base import BaseDriver


class GeminiDriver(BaseDriver):
    """
    Driver for Gemini's function calling format.

    Supports Gemini tool definitions and function call responses.
    """

    SUPPORTED_MODEL_PREFIXES = ("gemini-",)
    FUNCTION_CALL_TYPE = "function_call"
    FUNCTION_CALL_KEY = "functionCall"
    FUNCTION_CALL_FALLBACK_KEY = "function_call"
    DEFAULT_CALL_ID_PREFIX = "gemini_call_"

    def can_handle(self, profile: ModelProfile) -> int:
        """
        Score capability to handle the model profile.

        Returns 100 for Gemini models, 0 otherwise.
        """
        model_name = profile.name.lower()

        for prefix in self.SUPPORTED_MODEL_PREFIXES:
            if model_name.startswith(prefix):
                return 100

        return 0

    def can_handle_response(self, response: Any) -> int:
        """
        Score capability to parse the response based on Gemini fingerprint.

        Returns 100 for responses containing function call blocks.
        """
        try:
            calls = self._extract_function_calls(response)
            return 100 if calls else 0
        except Exception:
            return 0

    def render(self, tools: List[ToolMetadata]) -> List[Dict[str, Any]]:
        """
        Convert tools to Gemini's function tool schema.

        Returns a list of tool definitions in Gemini-compatible format:
        [
            {
                "type": "function",
                "name": "...",
                "description": "...",
                "parameters": { JSON Schema }
            }
        ]
        """
        result = []

        for tool in tools:
            if tool.parameters_model:
                schema = tool.parameters_model.model_json_schema()
                schema.pop("title", None)
            else:
                schema = {"type": "object", "properties": {}}

            tool_def = {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": schema,
            }
            result.append(tool_def)

        return result

    def parse(self, response: Any) -> List[ToolCall]:
        """
        Parse Gemini response to extract tool calls.

        Supports:
        - response.function_calls style list
        - candidates[*].content.parts functionCall entries
        - outputs with type=function_call
        """
        function_calls = self._extract_function_calls(response)
        if not function_calls:
            raise UnsupportedResponseFormatError(
                "gemini",
                f"Cannot extract function calls from response type: {type(response)}",
            )

        results = []
        for index, call_data in enumerate(function_calls):
            try:
                call = self._parse_function_call(call_data, index)
                results.append(call)
            except Exception as e:
                raise UnsupportedResponseFormatError(
                    "gemini",
                    f"Failed to parse function call: {e}",
                )

        return results

    def _extract_function_calls(self, response: Any) -> List[Dict[str, Any]]:
        if isinstance(response, dict):
            calls = self._extract_from_response_dict(response)
            if calls:
                return calls
            return []

        if isinstance(response, list):
            calls = self._coerce_call_list(response)
            if self._list_contains_function_calls(calls):
                return calls

            calls = self._extract_calls_from_outputs(response)
            if calls:
                return calls

        return []

    def _extract_from_response_dict(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        if "function_calls" in response:
            return self._coerce_call_list(response["function_calls"])

        if "candidates" in response:
            calls = self._extract_calls_from_candidates(response["candidates"])
            if calls:
                return calls

        if "outputs" in response:
            calls = self._extract_calls_from_outputs(response["outputs"])
            if calls:
                return calls

        if "content" in response:
            calls = self._extract_calls_from_content(response["content"])
            if calls:
                return calls

        return []

    def _extract_calls_from_candidates(self, candidates: Any) -> List[Dict[str, Any]]:
        if not isinstance(candidates, list):
            return []

        calls: List[Dict[str, Any]] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            calls.extend(self._extract_calls_from_content(candidate.get("content")))
        return calls

    def _extract_calls_from_content(self, content: Any) -> List[Dict[str, Any]]:
        if content is None:
            return []

        if isinstance(content, dict):
            return self._extract_calls_from_parts(content.get("parts"))

        if isinstance(content, list):
            return self._extract_calls_from_parts(content)

        return []

    def _extract_calls_from_parts(self, parts: Any) -> List[Dict[str, Any]]:
        if not isinstance(parts, list):
            return []

        calls: List[Dict[str, Any]] = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            if self.FUNCTION_CALL_KEY in part:
                calls.append(part[self.FUNCTION_CALL_KEY])
                continue
            if self.FUNCTION_CALL_FALLBACK_KEY in part:
                calls.append(part[self.FUNCTION_CALL_FALLBACK_KEY])
                continue
            if part.get("type") == self.FUNCTION_CALL_TYPE:
                calls.append(part)
        return calls

    def _extract_calls_from_outputs(self, outputs: Any) -> List[Dict[str, Any]]:
        if not isinstance(outputs, list):
            return []

        calls: List[Dict[str, Any]] = []
        for output in outputs:
            if not isinstance(output, dict):
                continue
            if output.get("type") == self.FUNCTION_CALL_TYPE:
                calls.append(output)
                continue
            if self.FUNCTION_CALL_KEY in output:
                calls.append(output[self.FUNCTION_CALL_KEY])
                continue
            if self.FUNCTION_CALL_FALLBACK_KEY in output:
                calls.append(output[self.FUNCTION_CALL_FALLBACK_KEY])
        return calls

    def _coerce_call_list(self, value: Any) -> List[Dict[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [value]
        return []

    def _list_contains_function_calls(self, calls: List[Dict[str, Any]]) -> bool:
        return any(self._looks_like_function_call(call) for call in calls)

    def _looks_like_function_call(self, call: Dict[str, Any]) -> bool:
        if "name" in call:
            return True
        if self.FUNCTION_CALL_KEY in call:
            return True
        if self.FUNCTION_CALL_FALLBACK_KEY in call:
            return True
        return False

    def _parse_function_call(self, call_data: Dict[str, Any], index: int) -> ToolCall:
        call_info = self._unwrap_function_call(call_data)
        name = call_info.get("name", "")
        call_id = call_info.get("id") or call_info.get("call_id") or f"{self.DEFAULT_CALL_ID_PREFIX}{index}"

        raw_args = call_info.get("args")
        if raw_args is None:
            raw_args = call_info.get("arguments")
        if raw_args is None:
            raw_args = call_info.get("input")
        if raw_args is None:
            raw_args = {}

        arguments = self._parse_arguments(raw_args)

        return ToolCall(
            id=call_id,
            name=name,
            arguments=arguments,
            context={},
        )

    def _unwrap_function_call(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.FUNCTION_CALL_KEY in call_data and isinstance(call_data[self.FUNCTION_CALL_KEY], dict):
            return call_data[self.FUNCTION_CALL_KEY]
        if self.FUNCTION_CALL_FALLBACK_KEY in call_data and isinstance(
            call_data[self.FUNCTION_CALL_FALLBACK_KEY], dict
        ):
            return call_data[self.FUNCTION_CALL_FALLBACK_KEY]
        return call_data

    def _parse_arguments(self, raw_args: Any) -> Dict[str, Any]:
        if isinstance(raw_args, dict):
            return raw_args
        if isinstance(raw_args, str):
            return json.loads(raw_args)
        if raw_args is None:
            return {}
        raise ValueError(f"Unsupported arguments type: {type(raw_args)}")
