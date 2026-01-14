"""
End-to-end integration tests simulating real LLM interaction.

Tests cover:
- Complete workflow from tool registration to execution
- Middleware pipeline with audit and monitor
- Tool filtering and rendering
- Error handling scenarios
"""

import pytest
import json
from typing import Annotated

from uni_tool.core.universe import Universe
from uni_tool.core.models import Tag, Prefix
from uni_tool.drivers.openai import OpenAIDriver
from uni_tool.middlewares.audit import AuditMiddleware
from uni_tool.middlewares.monitor import MonitorMiddleware
from uni_tool.utils.injection import Injected


@pytest.fixture
def fresh_universe():
    """Create a completely fresh Universe for each test."""
    u = Universe()
    u._reset()
    u.register_driver("openai", OpenAIDriver())
    return u


class TestFullWorkflow:
    """Tests simulating complete LLM interaction workflow."""

    @pytest.mark.asyncio
    async def test_complete_finance_workflow(self, fresh_universe):
        """
        Test a complete finance-related workflow.

        Scenario:
        1. Register finance tools with tags
        2. Add audit and monitor middleware
        3. Render tools for LLM
        4. Parse mock LLM response
        5. Execute tools with context injection
        6. Verify results and metrics
        """
        universe = fresh_universe

        # Setup: Register middlewares
        audit = AuditMiddleware()
        monitor = MonitorMiddleware()
        universe.use(audit, critical=False)
        universe.use(monitor, critical=False)

        # Setup: Register finance tools
        @universe.tool(tags={"finance", "query"})
        async def get_balance(
            currency: str,
            user_id: Annotated[str, Injected("uid")],
        ) -> dict:
            """Get the user's balance in the specified currency.

            Args:
                currency: The currency code (e.g., USD, EUR).
            """
            balances = {"USD": 1000.0, "EUR": 850.0, "JPY": 110000.0}
            return {
                "user_id": user_id,
                "currency": currency,
                "balance": balances.get(currency, 0.0),
            }

        @universe.tool(tags={"finance", "transaction"})
        async def transfer_funds(
            amount: float,
            to_account: str,
            user_id: Annotated[str, Injected("uid")],
        ) -> dict:
            """Transfer funds to another account.

            Args:
                amount: Amount to transfer.
                to_account: Destination account ID.
            """
            return {
                "from_user": user_id,
                "to_account": to_account,
                "amount": amount,
                "status": "completed",
            }

        @universe.tool(tags={"admin"})
        def get_system_status() -> dict:
            """Get system status (admin only)."""
            return {"status": "healthy", "uptime": 99.9}

        # Step 1: Render finance tools for LLM (filter by tag)
        finance_schema = universe[Tag("finance")].render("openai")

        assert len(finance_schema) == 2  # Only finance tools
        tool_names = {t["function"]["name"] for t in finance_schema}
        assert tool_names == {"get_balance", "transfer_funds"}

        # Step 2: Verify schema format
        balance_tool = next(t for t in finance_schema if t["function"]["name"] == "get_balance")
        assert balance_tool["type"] == "function"
        assert "currency" in balance_tool["function"]["parameters"]["properties"]
        # user_id should NOT be in schema (it's injected)
        assert "user_id" not in balance_tool["function"]["parameters"]["properties"]

        # Step 3: Simulate LLM response with tool calls
        mock_llm_response = {
            "tool_calls": [
                {
                    "id": "call_balance",
                    "type": "function",
                    "function": {
                        "name": "get_balance",
                        "arguments": json.dumps({"currency": "USD"}),
                    },
                },
                {
                    "id": "call_transfer",
                    "type": "function",
                    "function": {
                        "name": "transfer_funds",
                        "arguments": json.dumps({"amount": 100.0, "to_account": "ACC_789"}),
                    },
                },
            ]
        }

        # Step 4: Dispatch with context injection
        results = await universe.dispatch(
            mock_llm_response,
            context={"uid": "user_001"},
        )

        # Step 5: Verify execution results
        assert len(results) == 2

        balance_result = results[0]
        assert balance_result.is_success
        assert balance_result.result["user_id"] == "user_001"
        assert balance_result.result["currency"] == "USD"
        assert balance_result.result["balance"] == 1000.0

        transfer_result = results[1]
        assert transfer_result.is_success
        assert transfer_result.result["from_user"] == "user_001"
        assert transfer_result.result["status"] == "completed"

        # Step 6: Verify audit records
        assert len(audit.records) == 2
        assert audit.records[0].tool_name == "get_balance"
        assert audit.records[1].tool_name == "transfer_funds"

        # Step 7: Verify metrics
        metrics = monitor.export()
        assert "get_balance" in metrics
        assert "transfer_funds" in metrics
        assert metrics["get_balance"]["call_count"] == 1
        assert metrics["get_balance"]["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_error_handling_flow(self, fresh_universe):
        """
        Test error handling in the full workflow.

        Scenario:
        - Tool that fails with missing context
        - Tool that raises an exception
        - Verify errors are properly captured
        """
        universe = fresh_universe
        audit = AuditMiddleware()
        universe.use(audit, critical=False)

        @universe.tool()
        async def secure_action(
            action: str,
            secret: Annotated[str, Injected("missing_secret")],
        ) -> str:
            """Perform a secure action requiring a secret."""
            return f"Performed {action} with {secret}"

        @universe.tool()
        def unstable_tool() -> str:
            """Tool that always fails."""
            raise RuntimeError("Service unavailable")

        # Test missing context key
        response1 = {
            "tool_calls": [
                {
                    "id": "call_secure",
                    "type": "function",
                    "function": {
                        "name": "secure_action",
                        "arguments": '{"action": "delete"}',
                    },
                }
            ]
        }

        results1 = await universe.dispatch(response1, context={})
        assert not results1[0].is_success
        assert "missing_secret" in results1[0].error

        # Test tool exception
        response2 = {
            "tool_calls": [
                {
                    "id": "call_unstable",
                    "type": "function",
                    "function": {
                        "name": "unstable_tool",
                        "arguments": "{}",
                    },
                }
            ]
        }

        results2 = await universe.dispatch(response2, context={})
        assert not results2[0].is_success
        assert "Service unavailable" in results2[0].error

        # Verify audit captured both failures
        assert len(audit.records) == 2
        assert audit.records[0].error is not None
        assert audit.records[1].error is not None

    @pytest.mark.asyncio
    async def test_mixed_sync_async_tools(self, fresh_universe):
        """Test workflow with mixed sync and async tools."""
        universe = fresh_universe

        @universe.tool()
        def sync_calculator(a: int, b: int) -> int:
            """Synchronous addition."""
            return a + b

        @universe.tool()
        async def async_calculator(x: int, y: int) -> int:
            """Asynchronous multiplication."""
            return x * y

        response = {
            "tool_calls": [
                {
                    "id": "call_sync",
                    "type": "function",
                    "function": {
                        "name": "sync_calculator",
                        "arguments": '{"a": 5, "b": 3}',
                    },
                },
                {
                    "id": "call_async",
                    "type": "function",
                    "function": {
                        "name": "async_calculator",
                        "arguments": '{"x": 4, "y": 7}',
                    },
                },
            ]
        }

        results = await universe.dispatch(response, context={})

        assert len(results) == 2
        assert results[0].result == 8  # 5 + 3
        assert results[1].result == 28  # 4 * 7


class TestToolFiltering:
    """Tests for tool filtering scenarios."""

    @pytest.mark.asyncio
    async def test_complex_expression_filtering(self, fresh_universe):
        """Test complex tool filtering with combined expressions."""
        universe = fresh_universe

        @universe.tool(tags={"api", "v1", "read"})
        def api_v1_read() -> str:
            return "v1_read"

        @universe.tool(tags={"api", "v1", "write"})
        def api_v1_write() -> str:
            return "v1_write"

        @universe.tool(tags={"api", "v2", "read"})
        def api_v2_read() -> str:
            return "v2_read"

        @universe.tool(tags={"internal"})
        def internal_tool() -> str:
            return "internal"

        # Test: Get all API tools
        api_tools = universe[Tag("api")].get_tools()
        assert len(api_tools) == 3

        # Test: Get only v1 read tools
        v1_read_tools = universe[Tag("v1") & Tag("read")].get_tools()
        assert len(v1_read_tools) == 1
        assert v1_read_tools[0].name == "api_v1_read"

        # Test: Get non-internal tools
        public_tools = universe[~Tag("internal")].get_tools()
        assert len(public_tools) == 3

        # Test: Get v1 or internal
        mixed_tools = universe[Tag("v1") | Tag("internal")].get_tools()
        assert len(mixed_tools) == 3  # 2 v1 + 1 internal


class TestBindDecorator:
    """Tests for @bind class decorator."""

    def test_bind_registers_all_methods(self, fresh_universe):
        """Test that @bind registers all public methods of a class."""
        universe = fresh_universe

        @universe.bind(prefix="math_", tags={"calculator"})
        class MathService:
            """Math service with multiple operations."""

            def add(self, a: int, b: int) -> int:
                """Add two numbers."""
                return a + b

            def multiply(self, x: int, y: int) -> int:
                """Multiply two numbers."""
                return x * y

            def _private(self) -> str:
                """Private method (should not be registered)."""
                return "private"

        # Verify tools were registered with prefix
        assert "math_add" in universe
        assert "math_multiply" in universe
        assert "_private" not in universe
        assert "math__private" not in universe

        # Verify tags were applied
        assert "calculator" in universe["math_add"].tags

    @pytest.mark.asyncio
    async def test_bound_methods_execute(self, fresh_universe):
        """Test that bound methods can be executed."""
        universe = fresh_universe

        @universe.bind()
        class StringService:
            """String manipulation service."""

            def uppercase(self, text: str) -> str:
                """Convert to uppercase."""
                return text.upper()

        response = {
            "tool_calls": [
                {
                    "id": "call_upper",
                    "type": "function",
                    "function": {
                        "name": "uppercase",
                        "arguments": '{"text": "hello"}',
                    },
                }
            ]
        }

        results = await universe.dispatch(response, context={})
        assert results[0].result == "HELLO"
