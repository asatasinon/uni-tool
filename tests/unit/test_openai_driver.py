"""
Unit tests for OpenAI driver protocol adaptation.

Tests cover:
- Tool schema rendering (render method)
- Response parsing (parse method)
- Various response formats
- Error handling
"""

import pytest
import json

from uni_tool.core.models import ToolMetadata
from uni_tool.drivers.openai import OpenAIDriver
from uni_tool.core.errors import UnsupportedResponseFormatError
from pydantic import BaseModel, create_model


def create_tool_metadata(
    name: str,
    description: str,
    parameters_model: type[BaseModel] | None = None,
) -> ToolMetadata:
    """Create a ToolMetadata for testing."""
    return ToolMetadata(
        name=name,
        description=description,
        func=lambda: None,
        parameters_model=parameters_model,
    )


class TestOpenAIRender:
    """Tests for OpenAIDriver.render method."""

    def test_render_single_tool(self):
        """Test rendering a single tool."""
        # Create a parameters model
        ParamsModel = create_model(
            "TestParams",
            query=(str, ...),
            limit=(int, 10),
        )

        metadata = create_tool_metadata(
            name="search",
            description="Search for items",
            parameters_model=ParamsModel,
        )

        driver = OpenAIDriver()
        result = driver.render([metadata])

        assert len(result) == 1
        tool_def = result[0]

        assert tool_def["type"] == "function"
        assert tool_def["function"]["name"] == "search"
        assert tool_def["function"]["description"] == "Search for items"

        params = tool_def["function"]["parameters"]
        assert "properties" in params
        assert "query" in params["properties"]
        assert "limit" in params["properties"]

    def test_render_multiple_tools(self):
        """Test rendering multiple tools."""
        tools = [
            create_tool_metadata("tool_a", "Tool A"),
            create_tool_metadata("tool_b", "Tool B"),
            create_tool_metadata("tool_c", "Tool C"),
        ]

        driver = OpenAIDriver()
        result = driver.render(tools)

        assert len(result) == 3
        names = [t["function"]["name"] for t in result]
        assert names == ["tool_a", "tool_b", "tool_c"]

    def test_render_tool_without_parameters(self):
        """Test rendering a tool without parameters model."""
        metadata = create_tool_metadata(
            name="no_params",
            description="Tool without parameters",
            parameters_model=None,
        )

        driver = OpenAIDriver()
        result = driver.render([metadata])

        assert len(result) == 1
        params = result[0]["function"]["parameters"]
        assert params == {"type": "object", "properties": {}}

    def test_render_empty_list(self):
        """Test rendering empty tool list."""
        driver = OpenAIDriver()
        result = driver.render([])

        assert result == []

    def test_render_preserves_parameter_types(self):
        """Test that parameter types are preserved in schema."""
        ParamsModel = create_model(
            "TypedParams",
            name=(str, ...),
            count=(int, ...),
            active=(bool, False),
            score=(float, 0.0),
        )

        metadata = create_tool_metadata(
            name="typed_tool",
            description="Tool with typed params",
            parameters_model=ParamsModel,
        )

        driver = OpenAIDriver()
        result = driver.render([metadata])

        props = result[0]["function"]["parameters"]["properties"]

        # Check type mappings
        assert props["name"]["type"] == "string"
        assert props["count"]["type"] == "integer"
        assert props["active"]["type"] == "boolean"
        assert props["score"]["type"] == "number"


class TestOpenAIParse:
    """Tests for OpenAIDriver.parse method."""

    def test_parse_single_tool_call(self):
        """Test parsing a single tool call."""
        response = {
            "tool_calls": [
                {
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city": "Tokyo", "units": "celsius"}',
                    },
                }
            ]
        }

        driver = OpenAIDriver()
        calls = driver.parse(response)

        assert len(calls) == 1
        call = calls[0]

        assert call.id == "call_abc123"
        assert call.name == "get_weather"
        assert call.arguments == {"city": "Tokyo", "units": "celsius"}
        assert call.context == {}

    def test_parse_multiple_tool_calls(self):
        """Test parsing multiple tool calls."""
        response = {
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "tool_a", "arguments": "{}"},
                },
                {
                    "id": "call_2",
                    "type": "function",
                    "function": {"name": "tool_b", "arguments": '{"x": 1}'},
                },
            ]
        }

        driver = OpenAIDriver()
        calls = driver.parse(response)

        assert len(calls) == 2
        assert calls[0].name == "tool_a"
        assert calls[1].name == "tool_b"
        assert calls[1].arguments == {"x": 1}

    def test_parse_direct_list_format(self):
        """Test parsing when response is a direct list of tool calls."""
        response = [
            {
                "id": "call_direct",
                "type": "function",
                "function": {"name": "direct_tool", "arguments": "{}"},
            }
        ]

        driver = OpenAIDriver()
        calls = driver.parse(response)

        assert len(calls) == 1
        assert calls[0].name == "direct_tool"

    def test_parse_chat_completion_format(self):
        """Test parsing ChatCompletion response format."""
        response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_nested",
                                "type": "function",
                                "function": {
                                    "name": "nested_tool",
                                    "arguments": '{"key": "value"}',
                                },
                            }
                        ]
                    }
                }
            ]
        }

        driver = OpenAIDriver()
        calls = driver.parse(response)

        assert len(calls) == 1
        assert calls[0].name == "nested_tool"
        assert calls[0].arguments == {"key": "value"}

    def test_parse_dict_arguments(self):
        """Test parsing when arguments are already a dict (not JSON string)."""
        response = {
            "tool_calls": [
                {
                    "id": "call_dict",
                    "type": "function",
                    "function": {
                        "name": "dict_tool",
                        "arguments": {"pre_parsed": True},
                    },
                }
            ]
        }

        driver = OpenAIDriver()
        calls = driver.parse(response)

        assert calls[0].arguments == {"pre_parsed": True}

    def test_parse_empty_arguments(self):
        """Test parsing tool call with empty arguments."""
        response = {
            "tool_calls": [
                {
                    "id": "call_empty",
                    "type": "function",
                    "function": {"name": "empty_tool", "arguments": "{}"},
                }
            ]
        }

        driver = OpenAIDriver()
        calls = driver.parse(response)

        assert calls[0].arguments == {}

    def test_parse_invalid_format_raises_error(self):
        """Test that invalid format raises UnsupportedResponseFormatError."""
        driver = OpenAIDriver()

        with pytest.raises(UnsupportedResponseFormatError) as exc_info:
            driver.parse("invalid string response")

        assert "openai" in exc_info.value.driver

    def test_parse_missing_tool_calls_raises_error(self):
        """Test that missing tool_calls raises error."""
        driver = OpenAIDriver()

        with pytest.raises(UnsupportedResponseFormatError):
            driver.parse({"message": "no tool calls here"})

    def test_parse_invalid_json_in_arguments(self):
        """Test handling of invalid JSON in arguments."""
        response = {
            "tool_calls": [
                {
                    "id": "call_bad",
                    "type": "function",
                    "function": {
                        "name": "bad_tool",
                        "arguments": "not valid json{",
                    },
                }
            ]
        }

        driver = OpenAIDriver()

        with pytest.raises(UnsupportedResponseFormatError) as exc_info:
            driver.parse(response)

        assert "Failed to parse" in str(exc_info.value)


class TestOpenAIRoundTrip:
    """Tests for render -> parse round trip scenarios."""

    def test_render_and_validate_schema(self):
        """Test that rendered schema is valid JSON Schema."""
        ParamsModel = create_model(
            "ComplexParams",
            name=(str, ...),
            count=(int, ...),
            tags=(list[str], []),
        )

        metadata = create_tool_metadata(
            name="complex_tool",
            description="A complex tool",
            parameters_model=ParamsModel,
        )

        driver = OpenAIDriver()
        schema = driver.render([metadata])

        # Verify it's valid JSON
        json_str = json.dumps(schema)
        parsed = json.loads(json_str)

        assert parsed == schema
