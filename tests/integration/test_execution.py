"""
Integration tests for the basic execution flow.

Tests cover:
- End-to-end tool execution via dispatch
- Context injection during execution
- Sync and async tool execution
- Error handling during execution
"""

import pytest
from typing import Annotated

from uni_tool.core.universe import Universe
from uni_tool.core.models import ToolCall
from uni_tool.core.execution import execute_single_tool, execute_tool_calls
from uni_tool.drivers.openai import OpenAIDriver
from uni_tool.utils.injection import Injected


@pytest.fixture
def universe():
    """Create a fresh Universe instance with OpenAI driver."""
    u = Universe()
    u._reset()
    u.register_driver("openai", OpenAIDriver())
    return u


class TestBasicExecution:
    """Tests for basic tool execution."""

    @pytest.mark.asyncio
    async def test_execute_sync_tool(self, universe):
        """Test executing a synchronous tool."""

        @universe.tool()
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        call = ToolCall(
            id="call_001",
            name="add",
            arguments={"a": 1, "b": 2},
            context={},
        )

        result = await execute_single_tool(universe, call)

        assert result.is_success
        assert result.result == 3
        assert result.id == "call_001"
        assert "elapsed_ms" in result.meta

    @pytest.mark.asyncio
    async def test_execute_async_tool(self, universe):
        """Test executing an asynchronous tool."""

        @universe.tool()
        async def async_multiply(x: int, y: int) -> int:
            """Multiply two numbers."""
            return x * y

        call = ToolCall(
            id="call_002",
            name="async_multiply",
            arguments={"x": 3, "y": 4},
            context={},
        )

        result = await execute_single_tool(universe, call)

        assert result.is_success
        assert result.result == 12

    @pytest.mark.asyncio
    async def test_execute_with_injection(self, universe):
        """Test executing a tool with dependency injection."""

        @universe.tool()
        def get_user_data(
            field: str,
            user_id: Annotated[str, Injected("uid")],
        ) -> str:
            """Get user data field."""
            return f"User {user_id}'s {field}"

        call = ToolCall(
            id="call_003",
            name="get_user_data",
            arguments={"field": "email"},
            context={"uid": "user_123"},
        )

        result = await execute_single_tool(universe, call)

        assert result.is_success
        assert result.result == "User user_123's email"

    @pytest.mark.asyncio
    async def test_execute_missing_context_key(self, universe):
        """Test executing with missing context key."""

        @universe.tool()
        def needs_context(
            data: str,
            secret: Annotated[str, Injected("missing_key")],
        ) -> str:
            """Tool needing context."""
            return f"{secret}: {data}"

        call = ToolCall(
            id="call_004",
            name="needs_context",
            arguments={"data": "test"},
            context={},  # Missing "missing_key"
        )

        result = await execute_single_tool(universe, call)

        assert not result.is_success
        assert "missing_key" in result.error
        assert result.meta.get("error_type") == "MissingContextKeyError"

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self, universe):
        """Test executing a nonexistent tool."""
        call = ToolCall(
            id="call_005",
            name="nonexistent_tool",
            arguments={},
            context={},
        )

        result = await execute_single_tool(universe, call)

        assert not result.is_success
        assert "nonexistent_tool" in result.error
        assert result.meta.get("error_type") == "ToolNotFoundError"

    @pytest.mark.asyncio
    async def test_execute_tool_with_exception(self, universe):
        """Test handling exceptions during tool execution."""

        @universe.tool()
        def failing_tool(x: int) -> int:
            """Tool that always fails."""
            raise ValueError("Intentional failure")

        call = ToolCall(
            id="call_006",
            name="failing_tool",
            arguments={"x": 1},
            context={},
        )

        result = await execute_single_tool(universe, call)

        assert not result.is_success
        assert "Intentional failure" in result.error
        assert result.meta.get("error_type") == "ValueError"


class TestMultipleToolExecution:
    """Tests for executing multiple tools."""

    @pytest.mark.asyncio
    async def test_execute_multiple_tools(self, universe):
        """Test executing multiple tool calls."""

        @universe.tool()
        def tool_a() -> str:
            """Tool A."""
            return "A"

        @universe.tool()
        def tool_b() -> str:
            """Tool B."""
            return "B"

        calls = [
            ToolCall(id="call_a", name="tool_a", arguments={}, context={}),
            ToolCall(id="call_b", name="tool_b", arguments={}, context={}),
        ]

        results = await execute_tool_calls(universe, calls)

        assert len(results) == 2
        assert results[0].result == "A"
        assert results[1].result == "B"

    @pytest.mark.asyncio
    async def test_partial_failure_in_batch(self, universe):
        """Test that failures don't stop other executions."""

        @universe.tool()
        def success_tool() -> str:
            """Successful tool."""
            return "success"

        @universe.tool()
        def fail_tool() -> str:
            """Failing tool."""
            raise RuntimeError("Failed!")

        calls = [
            ToolCall(id="call_success", name="success_tool", arguments={}, context={}),
            ToolCall(id="call_fail", name="fail_tool", arguments={}, context={}),
        ]

        results = await execute_tool_calls(universe, calls)

        assert len(results) == 2
        assert results[0].is_success
        assert results[0].result == "success"
        assert not results[1].is_success
        assert "Failed!" in results[1].error


class TestDriverIntegration:
    """Tests for driver integration."""

    @pytest.mark.asyncio
    async def test_dispatch_with_openai_format(self, universe):
        """Test dispatching with OpenAI response format."""

        @universe.tool()
        def echo(message: str) -> str:
            """Echo the message."""
            return message

        # Simulate OpenAI response
        response = {
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "echo",
                        "arguments": '{"message": "Hello, World!"}',
                    },
                }
            ]
        }

        results = await universe.dispatch(response, context={})

        assert len(results) == 1
        assert results[0].is_success
        assert results[0].result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_dispatch_with_context(self, universe):
        """Test dispatching with context injection."""

        @universe.tool()
        def greet_user(
            greeting: str,
            user_name: Annotated[str, Injected("name")],
        ) -> str:
            """Greet the user."""
            return f"{greeting}, {user_name}!"

        response = {
            "tool_calls": [
                {
                    "id": "call_456",
                    "type": "function",
                    "function": {
                        "name": "greet_user",
                        "arguments": '{"greeting": "Hello"}',
                    },
                }
            ]
        }

        results = await universe.dispatch(
            response,
            context={"name": "Alice"},
        )

        assert len(results) == 1
        assert results[0].result == "Hello, Alice!"

    def test_render_tools_to_openai_schema(self, universe):
        """Test rendering tools to OpenAI schema format."""

        @universe.tool(tags={"math"})
        def calculate(
            expression: str,
            precision: int = 2,
        ) -> float:
            """Calculate a mathematical expression.

            Args:
                expression: The expression to evaluate.
                precision: Number of decimal places.
            """
            return eval(expression)

        schema = universe.render("openai")

        assert len(schema) == 1
        tool_def = schema[0]

        assert tool_def["type"] == "function"
        assert tool_def["function"]["name"] == "calculate"
        assert tool_def["function"]["description"] == "Calculate a mathematical expression."

        params = tool_def["function"]["parameters"]
        assert "expression" in params.get("properties", {})
        assert "precision" in params.get("properties", {})
