"""
UniTools SDK - 中间件示例

展示如何使用内置中间件和自定义中间件：
- AuditMiddleware: 审计日志
- MonitorMiddleware: 性能监控
- 自定义中间件: 权限检查、速率限制等
"""

import asyncio
import time
from typing import Any

from uni_tool import (
    universe,
    ToolCall,
    Tag,
    AuditMiddleware,
    MonitorMiddleware,
)


# =============================================================================
# 1. 内置中间件
# =============================================================================

# 审计中间件 - 记录所有工具调用
audit = AuditMiddleware(max_records=1000)
universe.use(audit, critical=False)

# 监控中间件 - 收集性能指标
monitor = MonitorMiddleware(
    on_record=lambda name, duration, success: print(
        f"  [Monitor] {name}: {duration:.2f}ms {'OK' if success else 'FAIL'}"
    )
)
universe.use(monitor, critical=False)


# =============================================================================
# 2. 自定义中间件 - 权限检查
# =============================================================================


async def permission_middleware(call: ToolCall, next_handler: Any) -> Any:
    """检查用户是否有权限执行该工具。"""
    user_role = call.context.get("role", "guest")
    tool_name = call.name

    # 定义权限规则
    admin_only_tools = {"delete_user", "reset_system"}

    if tool_name in admin_only_tools and user_role != "admin":
        raise PermissionError(f"Tool '{tool_name}' requires admin role")

    print(f"  [Permission] {tool_name}: role={user_role} -> allowed")
    return await next_handler(call)


# 注册权限中间件（critical=True 表示失败会中止执行）
universe.use(permission_middleware, critical=True)


# =============================================================================
# 3. 自定义中间件 - 速率限制
# =============================================================================


class RateLimitMiddleware:
    """简单的速率限制中间件。"""

    def __init__(self, max_calls_per_second: int = 10):
        self.max_calls = max_calls_per_second
        self.call_times: list[float] = []

    async def __call__(self, call: ToolCall, next_handler: Any) -> Any:
        now = time.time()

        # 清理 1 秒前的记录
        self.call_times = [t for t in self.call_times if now - t < 1.0]

        if len(self.call_times) >= self.max_calls:
            raise RuntimeError(f"Rate limit exceeded: {self.max_calls}/s")

        self.call_times.append(now)
        print(f"  [RateLimit] {call.name}: {len(self.call_times)}/{self.max_calls}")
        return await next_handler(call)


rate_limiter = RateLimitMiddleware(max_calls_per_second=5)
universe.use(rate_limiter, critical=True)


# =============================================================================
# 4. 作用域中间件 - 仅对特定工具生效
# =============================================================================


async def finance_logger(call: ToolCall, next_handler: Any) -> Any:
    """仅记录金融相关工具的调用。"""
    print(f"  [FinanceLog] Starting {call.name} with args: {call.arguments}")
    result = await next_handler(call)
    print(f"  [FinanceLog] Completed {call.name}")
    return result


# 仅对带有 'finance' 标签的工具生效
universe.use(finance_logger, critical=False, scope=Tag("finance"))


# =============================================================================
# 5. 注册测试工具
# =============================================================================


@universe.tool(tags={"finance"})
async def get_account(account_id: str) -> dict:
    """Get account information.

    Args:
        account_id: The account ID.
    """
    await asyncio.sleep(0.05)  # 模拟数据库查询
    return {"id": account_id, "balance": 1000.0, "status": "active"}


@universe.tool(tags={"utility"})
def echo(message: str) -> str:
    """Echo back the message.

    Args:
        message: Message to echo.
    """
    return f"Echo: {message}"


@universe.tool(tags={"admin"})
def delete_user(user_id: str) -> dict:
    """Delete a user (admin only).

    Args:
        user_id: The user ID to delete.
    """
    return {"deleted": user_id, "status": "success"}


# =============================================================================
# 6. 主程序
# =============================================================================


async def main():
    print("=" * 60)
    print("UniTools SDK - Middleware Demo")
    print("=" * 60)

    # --- 测试 1: 正常调用 ---
    print("\n[Test 1] Normal call with all middlewares:")
    response1 = {
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "get_account",
                    "arguments": '{"account_id": "ACC_001"}',
                },
            }
        ]
    }

    results1 = await universe.dispatch(response1, context={"role": "user"})
    print(f"  Result: {results1[0].result}")

    # --- 测试 2: 权限拒绝 ---
    print("\n[Test 2] Permission denied (non-admin calling admin tool):")
    response2 = {
        "tool_calls": [
            {
                "id": "call_2",
                "type": "function",
                "function": {
                    "name": "delete_user",
                    "arguments": '{"user_id": "user_123"}',
                },
            }
        ]
    }

    results2 = await universe.dispatch(response2, context={"role": "user"})
    print(f"  Error: {results2[0].error}")

    # --- 测试 3: 管理员调用 ---
    print("\n[Test 3] Admin calling admin tool:")
    results3 = await universe.dispatch(response2, context={"role": "admin"})
    print(f"  Result: {results3[0].result}")

    # --- 测试 4: 多个并发调用 ---
    print("\n[Test 4] Multiple concurrent calls:")
    response4 = {
        "tool_calls": [
            {
                "id": f"call_{i}",
                "type": "function",
                "function": {
                    "name": "echo",
                    "arguments": f'{{"message": "msg_{i}"}}',
                },
            }
            for i in range(4)
        ]
    }

    results4 = await universe.dispatch(response4, context={"role": "user"})
    for r in results4:
        print(f"  {r.id}: {r.result}")

    # --- 查看审计记录 ---
    print("\n[Audit Records]")
    for record in audit.records:
        status = "OK" if record.error is None else "ERROR"
        print(f"  {record.tool_name}: {record.elapsed_ms:.2f}ms [{status}]")

    # --- 查看性能指标 ---
    print("\n[Performance Metrics]")
    for name, m in monitor.export().items():
        print(f"  {name}: calls={m['call_count']}, avg={m['avg_duration_ms']:.2f}ms")


if __name__ == "__main__":
    asyncio.run(main())
