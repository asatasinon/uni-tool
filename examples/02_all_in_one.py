"""
UniTools SDK - All-in-One 完整示例

展示所有核心功能：
- 工具注册（同步/异步）
- 上下文注入（Injected）
- 标签过滤（Tag）
- 中间件（Audit/Monitor）
- 多协议支持
- 类绑定（@bind）
"""

import asyncio
import json
from typing import Annotated

from uni_tool import (
    universe,
    Injected,
    Tag,
    AuditMiddleware,
    MonitorMiddleware,
)


# =============================================================================
# 1. 中间件设置
# =============================================================================

audit = AuditMiddleware(max_records=100)
monitor = MonitorMiddleware()

universe.use(audit, critical=False)
universe.use(monitor, critical=False)


# =============================================================================
# 2. 工具注册 - 使用装饰器
# =============================================================================


@universe.tool(tags={"finance", "query"})
async def get_balance(
    currency: str,
    user_id: Annotated[str, Injected("uid")],  # 从上下文注入，不暴露给 LLM
) -> dict:
    """Get user account balance.

    Args:
        currency: Currency code (USD, EUR, CNY).
    """
    # 模拟数据库查询
    balances = {
        "user_001": {"USD": 1000.0, "EUR": 850.0, "CNY": 7200.0},
        "user_002": {"USD": 500.0, "EUR": 425.0, "CNY": 3600.0},
    }
    user_balances = balances.get(user_id, {})
    return {
        "user_id": user_id,
        "currency": currency,
        "balance": user_balances.get(currency, 0.0),
    }


@universe.tool(tags={"finance", "transaction"})
async def transfer_funds(
    amount: float,
    to_account: str,
    user_id: Annotated[str, Injected("uid")],
    auth_token: Annotated[str, Injected("token")],  # 敏感信息从上下文注入
) -> dict:
    """Transfer funds to another account.

    Args:
        amount: Amount to transfer.
        to_account: Destination account ID.
    """
    # 验证 token（示例）
    if not auth_token.startswith("Bearer"):
        return {"status": "error", "message": "Invalid token"}

    return {
        "from": user_id,
        "to": to_account,
        "amount": amount,
        "status": "completed",
        "transaction_id": "TXN_12345",
    }


@universe.tool(tags={"utility"})
def calculate(expression: str) -> float:
    """Evaluate a mathematical expression (sync tool).

    Args:
        expression: Math expression like '2 + 3 * 4'.
    """
    # 安全的数学表达式求值
    allowed_chars = set("0123456789+-*/.(). ")
    if not all(c in allowed_chars for c in expression):
        raise ValueError("Invalid characters in expression")
    return eval(expression)


@universe.tool(tags={"admin"})
def get_system_status() -> dict:
    """Get system health status (admin only)."""
    return {
        "status": "healthy",
        "uptime_hours": 720,
        "active_users": 1234,
    }


# =============================================================================
# 3. 类绑定 - 批量注册服务方法
# =============================================================================


@universe.bind(prefix="weather_", tags={"weather", "api"})
class WeatherService:
    """Weather information service."""

    def get_current(self, city: str) -> dict:
        """Get current weather for a city.

        Args:
            city: City name.
        """
        # 模拟天气数据
        return {
            "city": city,
            "temperature": 22,
            "condition": "Sunny",
            "humidity": 45,
        }

    def get_forecast(self, city: str, days: int = 3) -> list:
        """Get weather forecast.

        Args:
            city: City name.
            days: Number of days (1-7).
        """
        return [{"day": i + 1, "temperature": 20 + i, "condition": "Clear"} for i in range(min(days, 7))]


# =============================================================================
# 4. 主程序
# =============================================================================


async def main():
    print("=" * 60)
    print("UniTools SDK - All-in-One Demo")
    print("=" * 60)

    # --- 查看所有已注册工具 ---
    print("\n[1] All registered tools:")
    for name in universe.tool_names:
        tool = universe.get(name)
        print(f"  - {name}: tags={tool.tags}")

    # --- 按标签过滤并渲染 ---
    print("\n[2] Finance tools schema (for LLM):")
    finance_schema = universe[Tag("finance")].render("openai")
    for tool in finance_schema:
        print(f"  - {tool['function']['name']}")
        # 注意：user_id 和 auth_token 不会出现在 schema 中
        print(f"    params: {list(tool['function']['parameters']['properties'].keys())}")

    # --- 模拟 LLM 响应并执行 ---
    print("\n[3] Executing tool calls:")

    # 用户上下文（包含敏感信息，不传给 LLM）
    user_context = {
        "uid": "user_001",
        "token": "Bearer abc123xyz",
    }

    # 模拟 LLM 返回多个工具调用
    llm_response = {
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "get_balance",
                    "arguments": json.dumps({"currency": "USD"}),
                },
            },
            {
                "id": "call_2",
                "type": "function",
                "function": {
                    "name": "transfer_funds",
                    "arguments": json.dumps({"amount": 100.0, "to_account": "ACC_789"}),
                },
            },
            {
                "id": "call_3",
                "type": "function",
                "function": {
                    "name": "weather_get_current",
                    "arguments": json.dumps({"city": "Beijing"}),
                },
            },
        ]
    }

    # 执行（并行执行所有工具调用）
    results = await universe.dispatch(llm_response, context=user_context)

    for result in results:
        status = "OK" if result.is_success else "FAILED"
        print(f"  [{result.id}] {status}: {result.result}")

    # --- 使用 tool_filter 限制可执行的工具 ---
    print("\n[4] Execute with tool filter (finance only):")

    mixed_response = {
        "tool_calls": [
            {
                "id": "call_finance",
                "type": "function",
                "function": {
                    "name": "get_balance",
                    "arguments": json.dumps({"currency": "EUR"}),
                },
            },
            {
                "id": "call_admin",
                "type": "function",
                "function": {
                    "name": "get_system_status",
                    "arguments": "{}",
                },
            },
        ]
    }

    # 只允许 finance 标签的工具执行
    filtered_results = await universe.dispatch(
        mixed_response,
        context=user_context,
        tool_filter=Tag("finance"),
    )

    for result in filtered_results:
        if result.is_success:
            print(f"  [{result.id}] Allowed: {result.result}")
        else:
            print(f"  [{result.id}] Denied: {result.error}")

    # --- 审计记录 ---
    print("\n[5] Audit records:")
    for record in audit.records[-5:]:  # 最近 5 条
        status = "OK" if record.error is None else f"ERROR: {record.error}"
        print(f"  - {record.tool_name}: {record.elapsed_ms:.2f}ms [{status}]")

    # --- 性能指标 ---
    print("\n[6] Performance metrics:")
    metrics = monitor.export()
    for tool_name, m in metrics.items():
        print(f"  - {tool_name}:")
        print(f"      calls: {m['call_count']}, success_rate: {m['success_rate']:.0%}")
        print(f"      avg_duration: {m['avg_duration_ms']:.2f}ms")


if __name__ == "__main__":
    asyncio.run(main())
