"""
End-to-end integration tests simulating real LLM interaction.

Tests cover:
- Complete workflow from tool registration to execution
- Middleware pipeline with audit and monitor
- Tool filtering and rendering
- Error handling scenarios
- Parallel execution performance
- Protocol auto-detection
- Tool filter denial accuracy
"""

import asyncio
import pytest
import json
import time
from typing import Annotated

from uni_tool.core.universe import Universe
from uni_tool.filters import Tag, ToolName
from uni_tool.drivers.openai import OpenAIDriver
from uni_tool.drivers.anthropic import AnthropicDriver
from uni_tool.drivers.xml import XMLDriver
from uni_tool.drivers.markdown import MarkdownDriver
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
        api_tools = universe[Tag("api")].tools
        assert len(api_tools) == 3

        # Test: Get only v1 read tools
        v1_read_tools = universe[Tag("v1") & Tag("read")].tools
        assert len(v1_read_tools) == 1
        assert v1_read_tools[0].name == "api_v1_read"

        # Test: Get non-internal tools
        public_tools = universe[~Tag("internal")].tools
        assert len(public_tools) == 3

        # Test: Get v1 or internal
        mixed_tools = universe[Tag("v1") | Tag("internal")].tools
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

        # Verify tags were applied (use get() for name-based lookup)
        math_add_tool = universe.get("math_add")
        assert math_add_tool is not None
        assert "calculator" in math_add_tool.tags

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


class TestParallelExecution:
    """Tests for parallel execution performance (SC-002)."""

    @pytest.fixture
    def universe_with_drivers(self):
        """Create Universe with all drivers."""
        u = Universe()
        u._reset()
        u.register_driver("openai", OpenAIDriver())
        u.register_driver("anthropic", AnthropicDriver())
        u.register_driver("xml", XMLDriver())
        u.register_driver("markdown", MarkdownDriver())
        return u

    @pytest.mark.asyncio
    async def test_parallel_execution_performance_improvement(self, universe_with_drivers):
        """
        Test that parallel execution is at least 30% faster than sequential baseline.

        SC-002: In responses with at least 4 tool calls, total execution time
        should be reduced by at least 30% compared to sequential baseline.
        """
        universe = universe_with_drivers
        sleep_time = 0.1  # 100ms per tool

        @universe.tool()
        async def slow_tool(id: int) -> dict:
            """A tool that takes time to execute."""
            await asyncio.sleep(sleep_time)
            return {"id": id, "completed": True}

        # Create response with 4+ tool calls
        response = {
            "tool_calls": [
                {
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {"name": "slow_tool", "arguments": json.dumps({"id": i})},
                }
                for i in range(4)
            ]
        }

        # Measure parallel execution time
        start_time = time.perf_counter()
        results = await universe.dispatch(response, driver_or_model="openai", context={})
        parallel_time = time.perf_counter() - start_time

        # All should succeed
        assert len(results) == 4
        assert all(r.is_success for r in results)

        # Sequential baseline would be: 4 * 100ms = 400ms
        sequential_baseline = 4 * sleep_time

        # Parallel should be at least 30% faster
        # (1 - 0.3) * baseline = 0.7 * 400ms = 280ms
        expected_max_time = sequential_baseline * 0.7

        # Add some buffer for overhead (50ms)
        assert parallel_time < expected_max_time + 0.05, (
            f"Parallel execution ({parallel_time:.3f}s) should be at least 30% faster "
            f"than sequential baseline ({sequential_baseline:.3f}s). "
            f"Expected < {expected_max_time:.3f}s"
        )

    @pytest.mark.asyncio
    async def test_parallel_execution_maintains_order(self, universe_with_drivers):
        """Test that parallel execution maintains result order."""
        universe = universe_with_drivers

        @universe.tool()
        async def ordered_tool(order: int) -> int:
            """Tool that returns its order."""
            # Vary sleep time to try to cause reordering
            await asyncio.sleep(0.01 * (5 - order))
            return order

        response = {
            "tool_calls": [
                {
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {"name": "ordered_tool", "arguments": json.dumps({"order": i})},
                }
                for i in range(5)
            ]
        }

        results = await universe.dispatch(response, driver_or_model="openai", context={})

        # Results should be in the same order as calls
        assert [r.result for r in results] == [0, 1, 2, 3, 4]


class TestProtocolAutoDetection:
    """Tests for protocol auto-detection (SC-004)."""

    @pytest.fixture
    def universe_with_all_drivers(self):
        """Create Universe with all drivers."""
        u = Universe()
        u._reset()
        u.register_driver("openai", OpenAIDriver())
        u.register_driver("anthropic", AnthropicDriver())
        u.register_driver("xml", XMLDriver())
        u.register_driver("markdown", MarkdownDriver())
        return u

    @pytest.mark.asyncio
    async def test_auto_detect_openai_format(self, universe_with_all_drivers):
        """Test auto-detection of OpenAI format."""
        universe = universe_with_all_drivers

        @universe.tool()
        def echo(msg: str) -> str:
            return msg

        response = {
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "echo", "arguments": '{"msg": "openai"}'},
                }
            ]
        }

        # No driver specified - should auto-detect
        results = await universe.dispatch(response, context={})

        assert len(results) == 1
        assert results[0].is_success
        assert results[0].result == "openai"

    @pytest.mark.asyncio
    async def test_auto_detect_anthropic_format(self, universe_with_all_drivers):
        """Test auto-detection of Anthropic format."""
        universe = universe_with_all_drivers

        @universe.tool()
        def echo(msg: str) -> str:
            return msg

        response = {
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "echo",
                    "input": {"msg": "anthropic"},
                }
            ]
        }

        results = await universe.dispatch(response, context={})

        assert len(results) == 1
        assert results[0].is_success
        assert results[0].result == "anthropic"

    @pytest.mark.asyncio
    async def test_auto_detect_xml_format(self, universe_with_all_drivers):
        """Test auto-detection of XML format."""
        universe = universe_with_all_drivers

        @universe.tool()
        def echo(msg: str) -> str:
            return msg

        response = """
        <tool_call>
            <name>echo</name>
            <arguments>{"msg": "xml"}</arguments>
        </tool_call>
        """

        results = await universe.dispatch(response, context={})

        assert len(results) == 1
        assert results[0].is_success
        assert results[0].result == "xml"

    @pytest.mark.asyncio
    async def test_auto_detect_markdown_format(self, universe_with_all_drivers):
        """Test auto-detection of Markdown format."""
        universe = universe_with_all_drivers

        @universe.tool()
        def echo(msg: str) -> str:
            return msg

        response = """
        ```tool_call
        {"name": "echo", "arguments": {"msg": "markdown"}}
        ```
        """

        results = await universe.dispatch(response, context={})

        assert len(results) == 1
        assert results[0].is_success
        assert results[0].result == "markdown"

    @pytest.mark.asyncio
    async def test_protocol_detection_success_rate_100_percent(self, universe_with_all_drivers):
        """
        SC-004: Auto-detection success rate should be 100% for supported formats.
        """
        universe = universe_with_all_drivers

        @universe.tool()
        def echo(msg: str) -> str:
            return msg

        test_cases = [
            # OpenAI format
            {
                "tool_calls": [
                    {"id": "1", "type": "function", "function": {"name": "echo", "arguments": '{"msg": "1"}'}}
                ]
            },
            # Anthropic format
            {"content": [{"type": "tool_use", "id": "2", "name": "echo", "input": {"msg": "2"}}]},
            # XML format
            '<tool_call><name>echo</name><arguments>{"msg": "3"}</arguments></tool_call>',
            # Markdown format
            '```tool_call\n{"name": "echo", "arguments": {"msg": "4"}}\n```',
        ]

        success_count = 0
        for response in test_cases:
            results = await universe.dispatch(response, context={})
            if results and results[0].is_success:
                success_count += 1

        success_rate = success_count / len(test_cases)
        assert success_rate == 1.0, f"Detection success rate was {success_rate * 100}%, expected 100%"


class TestToolFilterDenialAccuracy:
    """Tests for tool filter denial accuracy (SC-003)."""

    @pytest.fixture
    def universe_with_tools(self):
        """Create Universe with multiple tools and drivers."""
        u = Universe()
        u._reset()
        u.register_driver("openai", OpenAIDriver())

        @u.tool(tags={"public", "api"})
        def public_api() -> str:
            return "public"

        @u.tool(tags={"admin", "api"})
        def admin_api() -> str:
            return "admin"

        @u.tool(tags={"internal"})
        def internal_tool() -> str:
            return "internal"

        return u

    @pytest.mark.asyncio
    async def test_filter_denies_non_matching_tools(self, universe_with_tools):
        """Test that filter correctly denies non-matching tools."""
        universe = universe_with_tools

        response = {
            "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "public_api", "arguments": "{}"}},
                {"id": "2", "type": "function", "function": {"name": "admin_api", "arguments": "{}"}},
                {"id": "3", "type": "function", "function": {"name": "internal_tool", "arguments": "{}"}},
            ]
        }

        # Filter to only allow public tools
        results = await universe.dispatch(
            response,
            driver_or_model="openai",
            context={},
            tool_filter=Tag("public"),
        )

        assert len(results) == 3

        # public_api should succeed
        assert results[0].is_success
        assert results[0].result == "public"

        # admin_api should be denied
        assert not results[1].is_success
        assert "denied by filter" in results[1].error
        assert results[1].meta.get("error_code") == "FILTER_DENIED"

        # internal_tool should be denied
        assert not results[2].is_success
        assert "denied by filter" in results[2].error

    @pytest.mark.asyncio
    async def test_tool_name_filter_exact_match(self, universe_with_tools):
        """Test ToolName filter for exact name matching."""
        universe = universe_with_tools

        response = {
            "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "public_api", "arguments": "{}"}},
                {"id": "2", "type": "function", "function": {"name": "admin_api", "arguments": "{}"}},
            ]
        }

        # Filter to only allow specific tool by name
        results = await universe.dispatch(
            response,
            driver_or_model="openai",
            context={},
            tool_filter=ToolName("public_api"),
        )

        assert len(results) == 2
        assert results[0].is_success  # public_api allowed
        assert not results[1].is_success  # admin_api denied

    @pytest.mark.asyncio
    async def test_filter_denial_accuracy_100_percent(self, universe_with_tools):
        """
        SC-003: Tool filter denial accuracy should be 100%.

        All denied calls should have error and should not execute.
        """
        universe = universe_with_tools

        # Track if internal_tool was actually called
        call_tracker = {"internal_called": False}

        @universe.tool(tags={"tracked"})
        def tracked_internal() -> str:
            call_tracker["internal_called"] = True
            return "should not run"

        response = {
            "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "tracked_internal", "arguments": "{}"}},
                {"id": "2", "type": "function", "function": {"name": "public_api", "arguments": "{}"}},
            ]
        }

        # Filter to deny tracked tools
        results = await universe.dispatch(
            response,
            driver_or_model="openai",
            context={},
            tool_filter=~Tag("tracked"),
        )

        # Verify denial accuracy
        denied_results = [r for r in results if not r.is_success and "denied" in (r.error or "")]
        allowed_results = [r for r in results if r.is_success]

        # tracked_internal should be denied and NOT executed
        assert len(denied_results) == 1
        assert denied_results[0].id == "1"
        assert not call_tracker["internal_called"], "Denied tool should not have been executed"

        # public_api should be allowed and executed
        assert len(allowed_results) == 1
        assert allowed_results[0].result == "public"

    @pytest.mark.asyncio
    async def test_filter_combined_expression(self, universe_with_tools):
        """Test complex filter expressions."""
        universe = universe_with_tools

        response = {
            "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "public_api", "arguments": "{}"}},
                {"id": "2", "type": "function", "function": {"name": "admin_api", "arguments": "{}"}},
                {"id": "3", "type": "function", "function": {"name": "internal_tool", "arguments": "{}"}},
            ]
        }

        # Filter: api AND NOT admin
        results = await universe.dispatch(
            response,
            driver_or_model="openai",
            context={},
            tool_filter=Tag("api") & ~Tag("admin"),
        )

        # public_api: has api, not admin -> allowed
        assert results[0].is_success

        # admin_api: has api but also admin -> denied
        assert not results[1].is_success

        # internal_tool: no api tag -> denied
        assert not results[2].is_success
