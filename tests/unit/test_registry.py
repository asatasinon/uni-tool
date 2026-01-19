"""
Unit tests for tool registration and dependency injection.

Tests cover:
- Basic tool registration via @tool decorator
- Duplicate tool detection
- Injected parameter handling
- Tool metadata extraction
"""

from typing import Annotated

import pytest

from uni_tool.core.errors import DuplicateToolError, ToolNotFoundError
from uni_tool.filters import Tag
from uni_tool.core.models import ToolMetadata
from uni_tool.core.universe import Universe
from uni_tool.utils.injection import Injected


@pytest.fixture
def universe():
    """Create a fresh Universe instance for each test."""
    u = Universe()
    u._reset()
    return u


class TestToolRegistration:
    """Tests for basic tool registration."""

    def test_register_simple_tool(self, universe):
        """Test registering a simple synchronous function."""

        @universe.tool()
        def greet(name: str) -> str:
            """Say hello to someone."""
            return f"Hello, {name}!"

        assert "greet" in universe
        assert len(universe) == 1

        metadata = universe.get("greet")
        assert metadata is not None
        assert metadata.name == "greet"
        assert metadata.description == "Say hello to someone."
        assert metadata.is_async is False

    def test_register_async_tool(self, universe):
        """Test registering an async function."""

        @universe.tool()
        async def async_greet(name: str) -> str:
            """Async greeting."""
            return f"Hello, {name}!"

        metadata = universe.get("async_greet")
        assert metadata is not None
        assert metadata.is_async is True

    def test_register_tool_with_custom_name(self, universe):
        """Test registering a tool with a custom name."""

        @universe.tool(name="custom_name")
        def my_function() -> str:
            """A function with custom name."""
            return "result"

        assert "custom_name" in universe
        assert "my_function" not in universe

    def test_register_tool_with_tags(self, universe):
        """Test registering a tool with tags."""

        @universe.tool(tags={"finance", "query"})
        def get_balance(account: str) -> float:
            """Get account balance."""
            return 100.0

        metadata = universe.get("get_balance")
        assert metadata is not None
        assert "finance" in metadata.tags
        assert "query" in metadata.tags

    def test_duplicate_tool_raises_error(self, universe):
        """Test that registering duplicate tool names raises an error."""

        @universe.tool()
        def duplicate_tool() -> str:
            """First tool."""
            return "first"

        with pytest.raises(DuplicateToolError) as exc_info:

            @universe.tool()
            def duplicate_tool() -> str:  # noqa: F811
                """Duplicate tool."""
                return "second"

        assert "duplicate_tool" in str(exc_info.value)

    def test_unregister_tool(self, universe):
        """Test unregistering a tool."""

        @universe.tool()
        def to_remove() -> str:
            """Tool to remove."""
            return "removed"

        assert "to_remove" in universe
        universe.unregister("to_remove")
        assert "to_remove" not in universe

    def test_unregister_nonexistent_raises_error(self, universe):
        """Test that unregistering a nonexistent tool raises an error."""
        with pytest.raises(ToolNotFoundError):
            universe.unregister("nonexistent")


class TestDependencyInjection:
    """Tests for dependency injection via Injected marker."""

    def test_injected_parameter_excluded_from_schema(self, universe):
        """Test that Injected parameters are not in the parameters model."""

        @universe.tool()
        def secure_action(
            action: str,
            user_id: Annotated[str, Injected("uid")],
        ) -> str:
            """Perform a secure action."""
            return f"User {user_id} performed {action}"

        metadata = universe.get("secure_action")
        assert metadata is not None

        # Check injected params
        assert "user_id" in metadata.injected_params
        assert metadata.injected_params["user_id"] == "uid"

        # Check that user_id is NOT in the Pydantic model
        if metadata.parameters_model:
            schema = metadata.parameters_model.model_json_schema()
            properties = schema.get("properties", {})
            assert "user_id" not in properties
            assert "action" in properties

    def test_injected_with_default_key(self, universe):
        """Test Injected without explicit key uses parameter name."""

        @universe.tool()
        def action_with_default(
            data: str,
            session_id: Annotated[str, Injected()],
        ) -> str:
            """Action using session."""
            return f"Session {session_id}: {data}"

        metadata = universe.get("action_with_default")
        assert metadata is not None
        # When no key is provided, it should use the parameter name
        assert metadata.injected_params["session_id"] == "session_id"

    def test_multiple_injected_parameters(self, universe):
        """Test multiple Injected parameters."""

        @universe.tool()
        def multi_inject(
            query: str,
            user_id: Annotated[str, Injected("uid")],
            org_id: Annotated[str, Injected("org")],
        ) -> str:
            """Query with multiple injections."""
            return f"{user_id}@{org_id}: {query}"

        metadata = universe.get("multi_inject")
        assert len(metadata.injected_params) == 2
        assert metadata.injected_params["user_id"] == "uid"
        assert metadata.injected_params["org_id"] == "org"


class TestToolExpression:
    """Tests for tool filtering with ToolExpression."""

    def test_filter_by_tag(self, universe):
        """Test filtering tools by tag."""

        @universe.tool(tags={"finance"})
        def finance_tool() -> str:
            """A finance tool."""
            return "finance"

        @universe.tool(tags={"admin"})
        def admin_tool() -> str:
            """An admin tool."""
            return "admin"

        # Filter by tag - now returns ToolSet
        tool_set = universe[Tag("finance")]
        tools = tool_set.tools

        assert len(tools) == 1
        assert tools[0].name == "finance_tool"

    def test_filter_by_combined_expression(self, universe):
        """Test filtering with combined expressions."""

        @universe.tool(tags={"api", "read"})
        def api_read() -> str:
            """Read API."""
            return "read"

        @universe.tool(tags={"api", "write"})
        def api_write() -> str:
            """Write API."""
            return "write"

        @universe.tool(tags={"internal"})
        def internal_tool() -> str:
            """Internal tool."""
            return "internal"

        # Filter: api AND read
        tool_set = universe[Tag("api") & Tag("read")]
        tools = tool_set.tools
        assert len(tools) == 1
        assert tools[0].name == "api_read"

        # Filter: api OR internal
        tool_set2 = universe[Tag("api") | Tag("internal")]
        tools2 = tool_set2.tools
        assert len(tools2) == 3

    def test_filter_by_tag_string(self, universe):
        """Test filtering tools by tag string - str is treated as Tag."""

        @universe.tool(tags={"finance"})
        def finance_tool() -> str:
            """A finance tool."""
            return "finance"

        @universe.tool(tags={"admin"})
        def admin_tool() -> str:
            """An admin tool."""
            return "admin"

        # Filter by tag string - now str is treated as Tag filter
        tool_set = universe["finance"]
        tools = tool_set.tools

        assert len(tools) == 1
        assert tools[0].name == "finance_tool"

    def test_access_by_name_via_get(self, universe):
        """Test accessing a tool by name via get() method."""

        @universe.tool()
        def named_tool() -> str:
            """A named tool."""
            return "named"

        # Use get() for name-based lookup
        tool = universe.get("named_tool")
        assert isinstance(tool, ToolMetadata)
        assert tool.name == "named_tool"

    def test_access_nonexistent_via_get_returns_none(self, universe):
        """Test that get() returns None for nonexistent tools."""
        tool = universe.get("nonexistent")
        assert tool is None

    def test_filter_nonexistent_tag_returns_empty_set(self, universe):
        """Test that filtering by nonexistent tag returns empty ToolSet."""

        @universe.tool(tags={"finance"})
        def finance_tool() -> str:
            """A finance tool."""
            return "finance"

        # Filter by nonexistent tag returns empty ToolSet
        tool_set = universe["nonexistent_tag"]
        assert len(tool_set) == 0
        assert not tool_set  # Empty ToolSet is falsy
