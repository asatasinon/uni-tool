"""
Unit tests for middleware pipeline.

Tests cover:
- Middleware execution order (Global -> Scoped -> Local)
- Deduplication by uid
- Exception isolation (critical vs non-critical)
- Audit middleware functionality
"""

import pytest
from typing import Any, List

from uni_tool.core.universe import Universe
from uni_tool.filters import Tag
from uni_tool.core.models import ToolCall, MiddlewareObj
from uni_tool.core.execution import execute_single_tool
from uni_tool.middlewares.base import (
    deduplicate_middlewares,
)
from uni_tool.middlewares.audit import AuditMiddleware, create_audit_middleware
from uni_tool.drivers.openai import OpenAIDriver


@pytest.fixture
def universe():
    """Create a fresh Universe instance."""
    u = Universe()
    u._reset()
    u.register_driver("openai", OpenAIDriver())
    return u


class TestMiddlewareOrdering:
    """Tests for middleware execution order."""

    @pytest.mark.asyncio
    async def test_global_middleware_executes_first(self, universe):
        """Test that global middlewares execute before scoped ones."""
        execution_order: List[str] = []

        async def global_mw(call: ToolCall, next_handler: Any) -> Any:
            execution_order.append("global")
            return await next_handler(call)

        async def scoped_mw(call: ToolCall, next_handler: Any) -> Any:
            execution_order.append("scoped")
            return await next_handler(call)

        # Register global middleware
        universe.use(global_mw, critical=True, scope=None)

        # Register scoped middleware (matches "test" tag)
        universe.use(scoped_mw, critical=True, scope=Tag("test"))

        @universe.tool(tags={"test"})
        def test_tool() -> str:
            """Test tool."""
            execution_order.append("tool")
            return "done"

        call = ToolCall(id="call_1", name="test_tool", arguments={}, context={})
        await execute_single_tool(universe, call)

        assert execution_order == ["global", "scoped", "tool"]

    @pytest.mark.asyncio
    async def test_local_middleware_executes_last(self, universe):
        """Test that local (tool-level) middlewares execute after global and scoped."""
        execution_order: List[str] = []

        async def global_mw(call: ToolCall, next_handler: Any) -> Any:
            execution_order.append("global")
            return await next_handler(call)

        async def local_mw(call: ToolCall, next_handler: Any) -> Any:
            execution_order.append("local")
            return await next_handler(call)

        universe.use(global_mw)

        local_mw_obj = MiddlewareObj(func=local_mw, critical=True)

        @universe.tool(middlewares=[local_mw_obj])
        def tool_with_local() -> str:
            """Tool with local middleware."""
            execution_order.append("tool")
            return "done"

        call = ToolCall(id="call_2", name="tool_with_local", arguments={}, context={})
        await execute_single_tool(universe, call)

        assert execution_order == ["global", "local", "tool"]

    @pytest.mark.asyncio
    async def test_onion_model_wrapping(self, universe):
        """Test that middleware wraps in onion model (LIFO for post-processing)."""
        events: List[str] = []

        async def outer_mw(call: ToolCall, next_handler: Any) -> Any:
            events.append("outer_pre")
            result = await next_handler(call)
            events.append("outer_post")
            return result

        async def inner_mw(call: ToolCall, next_handler: Any) -> Any:
            events.append("inner_pre")
            result = await next_handler(call)
            events.append("inner_post")
            return result

        universe.use(outer_mw)
        universe.use(inner_mw)

        @universe.tool()
        def onion_tool() -> str:
            """Onion tool."""
            events.append("execution")
            return "done"

        call = ToolCall(id="call_3", name="onion_tool", arguments={}, context={})
        await execute_single_tool(universe, call)

        # Outer pre -> Inner pre -> Execution -> Inner post -> Outer post
        assert events == [
            "outer_pre",
            "inner_pre",
            "execution",
            "inner_post",
            "outer_post",
        ]


class TestMiddlewareDeduplication:
    """Tests for middleware deduplication."""

    def test_deduplicate_by_uid(self):
        """Test that middlewares with same uid are deduplicated."""

        async def mw1(call, next_handler):
            return await next_handler(call)

        async def mw2(call, next_handler):
            return await next_handler(call)

        middlewares = [
            MiddlewareObj(func=mw1, critical=True, uid="shared_uid"),
            MiddlewareObj(func=mw2, critical=True, uid="shared_uid"),
        ]

        result = deduplicate_middlewares(middlewares)

        assert len(result) == 1
        # Later one wins
        assert result[0].func is mw2

    def test_preserve_different_uids(self):
        """Test that middlewares with different uids are preserved."""

        async def mw1(call, next_handler):
            return await next_handler(call)

        async def mw2(call, next_handler):
            return await next_handler(call)

        middlewares = [
            MiddlewareObj(func=mw1, critical=True, uid="uid_1"),
            MiddlewareObj(func=mw2, critical=True, uid="uid_2"),
        ]

        result = deduplicate_middlewares(middlewares)

        assert len(result) == 2


class TestExceptionIsolation:
    """Tests for exception isolation based on critical flag."""

    @pytest.mark.asyncio
    async def test_critical_middleware_propagates_exception(self, universe):
        """Test that critical middleware exceptions abort the pipeline."""

        async def failing_mw(call: ToolCall, next_handler: Any) -> Any:
            raise ValueError("Critical failure!")

        universe.use(failing_mw, critical=True)

        @universe.tool()
        def safe_tool() -> str:
            """Safe tool."""
            return "should not reach"

        call = ToolCall(id="call_4", name="safe_tool", arguments={}, context={})
        result = await execute_single_tool(universe, call)

        assert not result.is_success
        assert "Critical failure!" in result.error

    @pytest.mark.asyncio
    async def test_non_critical_middleware_continues_on_exception(self, universe):
        """Test that non-critical middleware exceptions don't abort the pipeline."""
        executed = False

        async def failing_mw(call: ToolCall, next_handler: Any) -> Any:
            raise ValueError("Non-critical failure!")

        universe.use(failing_mw, critical=False)

        @universe.tool()
        def robust_tool() -> str:
            """Robust tool."""
            nonlocal executed
            executed = True
            return "success"

        call = ToolCall(id="call_5", name="robust_tool", arguments={}, context={})
        result = await execute_single_tool(universe, call)

        assert result.is_success
        assert result.result == "success"
        assert executed is True


class TestAuditMiddleware:
    """Tests for the audit middleware."""

    @pytest.mark.asyncio
    async def test_audit_records_success(self, universe):
        """Test that audit middleware records successful calls."""
        audit = AuditMiddleware()
        universe.use(audit, critical=False)

        @universe.tool()
        def audited_tool(x: int) -> int:
            """Audited tool."""
            return x * 2

        call = ToolCall(
            id="audit_call_1",
            name="audited_tool",
            arguments={"x": 5},
            context={"user": "test"},
        )
        await execute_single_tool(universe, call)

        assert len(audit.records) == 1
        record = audit.records[0]

        assert record.tool_name == "audited_tool"
        assert record.call_id == "audit_call_1"
        assert record.arguments == {"x": 5}
        assert record.result == 10
        assert record.error is None
        assert "user" in record.context_keys

    @pytest.mark.asyncio
    async def test_audit_records_failure(self, universe):
        """Test that audit middleware records failed calls."""
        audit = AuditMiddleware()
        universe.use(audit, critical=False)

        @universe.tool()
        def failing_audited() -> str:
            """Failing audited tool."""
            raise RuntimeError("Audit this failure!")

        call = ToolCall(id="audit_call_2", name="failing_audited", arguments={}, context={})
        await execute_single_tool(universe, call)

        assert len(audit.records) == 1
        record = audit.records[0]

        assert record.tool_name == "failing_audited"
        assert record.error == "Audit this failure!"
        assert record.result is None

    @pytest.mark.asyncio
    async def test_audit_max_records_fifo(self, universe):
        """Test that audit middleware respects max_records with FIFO eviction."""
        audit = AuditMiddleware(max_records=2)
        universe.use(audit, critical=False)

        @universe.tool()
        def fifo_tool(n: int) -> int:
            """FIFO tool."""
            return n

        for i in range(3):
            call = ToolCall(
                id=f"fifo_{i}",
                name="fifo_tool",
                arguments={"n": i},
                context={},
            )
            await execute_single_tool(universe, call)

        assert len(audit.records) == 2
        # First record should be evicted
        assert audit.records[0].call_id == "fifo_1"
        assert audit.records[1].call_id == "fifo_2"

    def test_create_audit_middleware_factory(self):
        """Test the audit middleware factory function."""
        audit, mw_obj = create_audit_middleware(max_records=500, critical=True, uid="my_audit")

        assert isinstance(audit, AuditMiddleware)
        assert audit.max_records == 500
        assert mw_obj.critical is True
        assert mw_obj.uid == "my_audit"


class TestScopedMiddleware:
    """Tests for scoped middleware filtering."""

    @pytest.mark.asyncio
    async def test_scoped_middleware_applies_to_matching_tools(self, universe):
        """Test that scoped middleware only applies to matching tools."""
        finance_called = False
        admin_called = False

        async def finance_mw(call: ToolCall, next_handler: Any) -> Any:
            nonlocal finance_called
            finance_called = True
            return await next_handler(call)

        universe.use(finance_mw, scope=Tag("finance"))

        @universe.tool(tags={"finance"})
        def finance_tool() -> str:
            """Finance tool."""
            return "finance"

        @universe.tool(tags={"admin"})
        def admin_tool() -> str:
            """Admin tool."""
            nonlocal admin_called
            admin_called = True
            return "admin"

        # Call finance tool - middleware should run
        call1 = ToolCall(id="call_f", name="finance_tool", arguments={}, context={})
        await execute_single_tool(universe, call1)
        assert finance_called is True

        # Reset and call admin tool - middleware should NOT run
        finance_called = False
        call2 = ToolCall(id="call_a", name="admin_tool", arguments={}, context={})
        await execute_single_tool(universe, call2)
        assert finance_called is False
        assert admin_called is True
