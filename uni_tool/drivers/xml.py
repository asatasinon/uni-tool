"""
XML driver for UniTools SDK.

Implements protocol adaptation for XML-based tool calling format.
"""

from __future__ import annotations

import re
import json
from typing import Any, List
from xml.etree import ElementTree as ET

from uni_tool.drivers.base import BaseDriver
from uni_tool.core.models import ToolMetadata, ToolCall, ModelProfile
from uni_tool.core.errors import UnsupportedResponseFormatError


class XMLDriver(BaseDriver):
    """
    Driver for XML-based tool calling format.

    Supports tool calls embedded in XML format:
    <tool_call>
        <name>tool_name</name>
        <arguments>{"arg": "value"}</arguments>
    </tool_call>
    """

    # XML tool call pattern
    TOOL_CALL_PATTERN = re.compile(
        r"<tool_call[^>]*>(.*?)</tool_call>",
        re.DOTALL | re.IGNORECASE,
    )

    def can_handle(self, profile: ModelProfile) -> int:
        """
        Score capability to handle the model profile.

        Returns 30 as fallback for any model (XML is universal fallback).
        """
        # XML is a universal fallback
        if "XML_FALLBACK" in profile.capabilities:
            return 40

        # Low score as fallback
        return 10

    def can_handle_response(self, response: Any) -> int:
        """
        Score capability to parse the response based on XML fingerprint.

        Returns 100 for responses containing <tool_call> tags.
        """
        try:
            if isinstance(response, str):
                # Check for tool_call XML tags
                if "<tool_call" in response.lower() and "</tool_call>" in response.lower():
                    return 100

            if isinstance(response, dict):
                # Check for text content with XML
                text = response.get("text", "") or response.get("content", "")
                if isinstance(text, str) and "<tool_call" in text.lower():
                    return 100

            return 0
        except Exception:
            return 0

    def render(self, tools: List[ToolMetadata]) -> str:
        """
        Convert tools to XML format documentation.

        Returns XML describing available tools for prompt injection.
        """
        lines = ["<available_tools>"]

        for tool in tools:
            lines.append(f'  <tool name="{tool.name}">')
            lines.append(f"    <description>{tool.description}</description>")

            # Generate parameters from Pydantic model
            if tool.parameters_model:
                schema = tool.parameters_model.model_json_schema()
                properties = schema.get("properties", {})
                required = schema.get("required", [])

                if properties:
                    lines.append("    <parameters>")
                    for param_name, param_info in properties.items():
                        param_type = param_info.get("type", "string")
                        param_desc = param_info.get("description", "")
                        is_required = param_name in required
                        req_str = 'required="true"' if is_required else 'required="false"'
                        lines.append(
                            f'      <parameter name="{param_name}" type="{param_type}" {req_str}>'
                            f"{param_desc}</parameter>"
                        )
                    lines.append("    </parameters>")

            lines.append("  </tool>")

        lines.append("</available_tools>")
        return "\n".join(lines)

    def parse(self, response: Any) -> List[ToolCall]:
        """
        Parse XML response to extract tool calls.

        Supports tool_call XML format:
        <tool_call id="call_001">
            <name>tool_name</name>
            <arguments>{"arg": "value"}</arguments>
        </tool_call>
        """
        text = self._extract_text(response)
        results = []

        # Find all tool_call blocks
        matches = self.TOOL_CALL_PATTERN.findall(text)

        for i, match in enumerate(matches):
            try:
                call = self._parse_single_tool_call(match, i)
                results.append(call)
            except Exception as e:
                raise UnsupportedResponseFormatError(
                    "xml",
                    f"Failed to parse tool_call: {e}",
                )

        return results

    def _parse_single_tool_call(self, xml_content: str, index: int) -> ToolCall:
        """Parse a single tool_call XML block."""
        name, args_text = self._extract_name_and_args(xml_content)

        return ToolCall(
            id=f"xml_call_{index}",
            name=name,
            arguments=json.loads(args_text),
            context={},
        )

    def _extract_name_and_args(self, xml_content: str) -> tuple[str, str]:
        """Extract name and arguments from XML content."""
        try:
            wrapped = f"<root>{xml_content}</root>"
            root = ET.fromstring(wrapped)

            name_elem = root.find("name")
            args_elem = root.find("arguments")

            name = name_elem.text.strip() if name_elem is not None and name_elem.text else ""
            args_text = args_elem.text.strip() if args_elem is not None and args_elem.text else "{}"

            return name, args_text
        except ET.ParseError:
            # Fallback to regex parsing
            name_match = re.search(r"<name>(.*?)</name>", xml_content, re.DOTALL)
            args_match = re.search(r"<arguments>(.*?)</arguments>", xml_content, re.DOTALL)

            name = name_match.group(1).strip() if name_match else ""
            args_text = args_match.group(1).strip() if args_match else "{}"

            return name, args_text
