"""
Contract tests for protocol drivers.

Tests verify that all drivers implement the BaseDriver interface correctly
and produce consistent input/output for render/parse operations.
"""

import pytest
from typing import List, Dict

from pydantic import BaseModel

from uni_tool.drivers.base import BaseDriver
from uni_tool.drivers.openai import OpenAIDriver
from uni_tool.drivers.anthropic import AnthropicDriver
from uni_tool.drivers.deepseek import DeepSeekDriver
from uni_tool.drivers.gemini import GeminiDriver
from uni_tool.drivers.glm import GLMDriver
from uni_tool.drivers.xml import XMLDriver
from uni_tool.drivers.markdown import MarkdownDriver
from uni_tool.core.models import ToolMetadata, ToolCall, ModelProfile


class SampleParams(BaseModel):
    """Sample parameters model for testing."""

    query: str
    limit: int = 10


def create_sample_tool() -> ToolMetadata:
    """Create a sample tool for testing."""
    return ToolMetadata(
        name="search",
        description="Search for information",
        func=lambda x: x,
        is_async=False,
        parameters_model=SampleParams,
        injected_params={},
        tags={"search", "api"},
        middlewares=[],
    )


def create_sample_tools() -> List[ToolMetadata]:
    """Create multiple sample tools for testing."""
    return [
        create_sample_tool(),
        ToolMetadata(
            name="get_user",
            description="Get user information",
            func=lambda x: x,
            is_async=False,
            parameters_model=None,
            injected_params={},
            tags={"user"},
            middlewares=[],
        ),
    ]


class TestOpenAIDriverContract:
    """Contract tests for OpenAI driver."""

    @pytest.fixture
    def driver(self) -> OpenAIDriver:
        return OpenAIDriver()

    def test_implements_base_driver(self, driver: OpenAIDriver):
        """Test that driver implements BaseDriver interface."""
        assert isinstance(driver, BaseDriver)

    def test_render_returns_list(self, driver: OpenAIDriver):
        """Test that render returns a list."""
        tools = create_sample_tools()
        result = driver.render(tools)
        assert isinstance(result, list)

    def test_render_output_structure(self, driver: OpenAIDriver):
        """Test that render output has correct structure."""
        tools = create_sample_tools()
        result = driver.render(tools)

        for item in result:
            assert "type" in item
            assert item["type"] == "function"
            assert "function" in item
            assert "name" in item["function"]
            assert "description" in item["function"]
            assert "parameters" in item["function"]

    def test_parse_returns_tool_calls(self, driver: OpenAIDriver):
        """Test that parse returns list of ToolCall."""
        response = {
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {"name": "search", "arguments": '{"query": "test"}'},
                }
            ]
        }
        result = driver.parse(response)
        assert isinstance(result, list)
        assert all(isinstance(tc, ToolCall) for tc in result)

    def test_can_handle_openai_models(self, driver: OpenAIDriver):
        """Test can_handle scores OpenAI models highly."""
        profile = ModelProfile(name="gpt-4o", capabilities={"FC_NATIVE"})
        score = driver.can_handle(profile)
        assert score == 100

    def test_can_handle_response_openai_format(self, driver: OpenAIDriver):
        """Test can_handle_response recognizes OpenAI format."""
        response = {
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {"name": "search", "arguments": "{}"},
                }
            ]
        }
        score = driver.can_handle_response(response)
        assert score == 100


class TestAnthropicDriverContract:
    """Contract tests for Anthropic driver."""

    @pytest.fixture
    def driver(self) -> AnthropicDriver:
        return AnthropicDriver()

    def test_implements_base_driver(self, driver: AnthropicDriver):
        """Test that driver implements BaseDriver interface."""
        assert isinstance(driver, BaseDriver)

    def test_render_returns_list(self, driver: AnthropicDriver):
        """Test that render returns a list."""
        tools = create_sample_tools()
        result = driver.render(tools)
        assert isinstance(result, list)

    def test_render_output_structure(self, driver: AnthropicDriver):
        """Test that render output has correct structure."""
        tools = create_sample_tools()
        result = driver.render(tools)

        for item in result:
            assert "name" in item
            assert "description" in item
            assert "input_schema" in item

    def test_parse_returns_tool_calls(self, driver: AnthropicDriver):
        """Test that parse returns list of ToolCall."""
        response = {
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_001",
                    "name": "search",
                    "input": {"query": "test"},
                }
            ]
        }
        result = driver.parse(response)
        assert isinstance(result, list)
        assert all(isinstance(tc, ToolCall) for tc in result)

    def test_can_handle_anthropic_models(self, driver: AnthropicDriver):
        """Test can_handle scores Anthropic models highly."""
        profile = ModelProfile(name="claude-3-opus", capabilities={"FC_NATIVE"})
        score = driver.can_handle(profile)
        assert score == 100

    def test_can_handle_response_anthropic_format(self, driver: AnthropicDriver):
        """Test can_handle_response recognizes Anthropic format."""
        response = {
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_001",
                    "name": "search",
                    "input": {},
                }
            ]
        }
        score = driver.can_handle_response(response)
        assert score == 100


class TestGeminiDriverContract:
    """Contract tests for Gemini driver."""

    @pytest.fixture
    def driver(self) -> GeminiDriver:
        return GeminiDriver()

    def test_implements_base_driver(self, driver: GeminiDriver):
        """Test that driver implements BaseDriver interface."""
        assert isinstance(driver, BaseDriver)

    def test_render_returns_list(self, driver: GeminiDriver):
        """Test that render returns a list."""
        tools = create_sample_tools()
        result = driver.render(tools)
        assert isinstance(result, list)

    def test_render_output_structure(self, driver: GeminiDriver):
        """Test that render output has correct structure."""
        tools = create_sample_tools()
        result = driver.render(tools)

        for item in result:
            assert "type" in item
            assert item["type"] == "function"
            assert "name" in item
            assert "description" in item
            assert "parameters" in item

    def test_parse_returns_tool_calls(self, driver: GeminiDriver):
        """Test that parse returns list of ToolCall."""
        response = {
            "function_calls": [
                {
                    "id": "gemini_call_001",
                    "name": "search",
                    "args": {"query": "test"},
                }
            ]
        }
        result = driver.parse(response)
        assert isinstance(result, list)
        assert all(isinstance(tc, ToolCall) for tc in result)

    def test_can_handle_gemini_models(self, driver: GeminiDriver):
        """Test can_handle scores Gemini models highly."""
        profile = ModelProfile(name="gemini-2.5-flash", capabilities={"FC_NATIVE"})
        score = driver.can_handle(profile)
        assert score == 100

    def test_can_handle_response_gemini_format(self, driver: GeminiDriver):
        """Test can_handle_response recognizes Gemini format."""
        response = {
            "candidates": [{"content": {"parts": [{"functionCall": {"name": "search", "args": {"query": "test"}}}]}}]
        }
        score = driver.can_handle_response(response)
        assert score == 100


class TestDeepSeekDriverContract:
    """Contract tests for DeepSeek driver."""

    @pytest.fixture
    def driver(self) -> DeepSeekDriver:
        return DeepSeekDriver()

    def test_implements_base_driver(self, driver: DeepSeekDriver):
        """Test that driver implements BaseDriver interface."""
        assert isinstance(driver, BaseDriver)

    def test_parse_returns_tool_calls(self, driver: DeepSeekDriver):
        """Test that parse returns list of ToolCall."""
        response = {
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {"name": "search", "arguments": '{"query": "test"}'},
                }
            ]
        }
        result = driver.parse(response)
        assert isinstance(result, list)
        assert all(isinstance(tc, ToolCall) for tc in result)

    def test_can_handle_deepseek_models(self, driver: DeepSeekDriver):
        """Test can_handle scores DeepSeek models highly."""
        profile = ModelProfile(name="deepseek-chat", capabilities={"FC_NATIVE"})
        score = driver.can_handle(profile)
        assert score == 100


class TestGLMDriverContract:
    """Contract tests for GLM driver."""

    @pytest.fixture
    def driver(self) -> GLMDriver:
        return GLMDriver()

    def test_implements_base_driver(self, driver: GLMDriver):
        """Test that driver implements BaseDriver interface."""
        assert isinstance(driver, BaseDriver)

    def test_parse_returns_tool_calls(self, driver: GLMDriver):
        """Test that parse returns list of ToolCall."""
        response = {
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {"name": "search", "arguments": '{"query": "test"}'},
                }
            ]
        }
        result = driver.parse(response)
        assert isinstance(result, list)
        assert all(isinstance(tc, ToolCall) for tc in result)

    def test_can_handle_glm_models(self, driver: GLMDriver):
        """Test can_handle scores GLM models highly."""
        profile = ModelProfile(name="glm-4.5", capabilities={"FC_NATIVE"})
        score = driver.can_handle(profile)
        assert score == 100


class TestXMLDriverContract:
    """Contract tests for XML driver."""

    @pytest.fixture
    def driver(self) -> XMLDriver:
        return XMLDriver()

    def test_implements_base_driver(self, driver: XMLDriver):
        """Test that driver implements BaseDriver interface."""
        assert isinstance(driver, BaseDriver)

    def test_render_returns_string(self, driver: XMLDriver):
        """Test that render returns a string."""
        tools = create_sample_tools()
        result = driver.render(tools)
        assert isinstance(result, str)

    def test_render_output_structure(self, driver: XMLDriver):
        """Test that render output has correct XML structure."""
        tools = create_sample_tools()
        result = driver.render(tools)

        assert "<available_tools>" in result
        assert "</available_tools>" in result
        assert '<tool name="search">' in result

    def test_parse_returns_tool_calls(self, driver: XMLDriver):
        """Test that parse returns list of ToolCall."""
        response = """
        <tool_call>
            <name>search</name>
            <arguments>{"query": "test"}</arguments>
        </tool_call>
        """
        result = driver.parse(response)
        assert isinstance(result, list)
        assert all(isinstance(tc, ToolCall) for tc in result)

    def test_can_handle_xml_fallback(self, driver: XMLDriver):
        """Test can_handle scores XML_FALLBACK capability."""
        profile = ModelProfile(name="custom-model", capabilities={"XML_FALLBACK"})
        score = driver.can_handle(profile)
        assert score == 40

    def test_can_handle_response_xml_format(self, driver: XMLDriver):
        """Test can_handle_response recognizes XML format."""
        response = "<tool_call><name>search</name><arguments>{}</arguments></tool_call>"
        score = driver.can_handle_response(response)
        assert score == 100


class TestMarkdownDriverContract:
    """Contract tests for Markdown driver."""

    @pytest.fixture
    def driver(self) -> MarkdownDriver:
        return MarkdownDriver()

    def test_implements_base_driver(self, driver: MarkdownDriver):
        """Test that driver implements BaseDriver interface."""
        assert isinstance(driver, BaseDriver)

    def test_render_returns_string(self, driver: MarkdownDriver):
        """Test that render returns a string."""
        tools = create_sample_tools()
        result = driver.render(tools)
        assert isinstance(result, str)

    def test_render_output_structure(self, driver: MarkdownDriver):
        """Test that render output has correct Markdown structure."""
        tools = create_sample_tools()
        result = driver.render(tools)

        assert "# Available Tools" in result
        assert "## search" in result

    def test_parse_returns_tool_calls(self, driver: MarkdownDriver):
        """Test that parse returns list of ToolCall."""
        response = """
        ```tool_call
        {"name": "search", "arguments": {"query": "test"}}
        ```
        """
        result = driver.parse(response)
        assert isinstance(result, list)
        assert all(isinstance(tc, ToolCall) for tc in result)

    def test_can_handle_response_markdown_format(self, driver: MarkdownDriver):
        """Test can_handle_response recognizes Markdown format."""
        response = '```tool_call\n{"name": "search", "arguments": {}}\n```'
        score = driver.can_handle_response(response)
        assert score == 100

    def test_parse_action_format(self, driver: MarkdownDriver):
        """Test parsing Action/Action Input format."""
        response = """
        Action: search
        Action Input: {"query": "test"}
        """
        result = driver.parse(response)
        assert len(result) == 1
        assert result[0].name == "search"


class TestDriverConsistency:
    """Cross-driver consistency tests."""

    @pytest.fixture
    def all_drivers(self) -> Dict[str, BaseDriver]:
        return {
            "openai": OpenAIDriver(),
            "anthropic": AnthropicDriver(),
            "gemini": GeminiDriver(),
            "deepseek": DeepSeekDriver(),
            "glm": GLMDriver(),
            "xml": XMLDriver(),
            "markdown": MarkdownDriver(),
        }

    def test_all_drivers_render_same_tools(self, all_drivers: Dict[str, BaseDriver]):
        """Test that all drivers can render the same tools."""
        tools = create_sample_tools()

        for name, driver in all_drivers.items():
            result = driver.render(tools)
            assert result is not None, f"{name} driver failed to render"

    def test_all_drivers_have_can_handle(self, all_drivers: Dict[str, BaseDriver]):
        """Test that all drivers implement can_handle."""
        profile = ModelProfile(name="test-model", capabilities=set())

        for name, driver in all_drivers.items():
            score = driver.can_handle(profile)
            assert isinstance(score, int), f"{name} driver can_handle returned non-int"
            assert 0 <= score <= 100, f"{name} driver can_handle returned invalid score"

    def test_all_drivers_have_can_handle_response(self, all_drivers: Dict[str, BaseDriver]):
        """Test that all drivers implement can_handle_response."""
        response = "test response"

        for name, driver in all_drivers.items():
            score = driver.can_handle_response(response)
            assert isinstance(score, int), f"{name} driver can_handle_response returned non-int"
            assert 0 <= score <= 100, f"{name} driver can_handle_response returned invalid score"
