import asyncio
from typing import Any

from uni_tool import Universe
from uni_tool.core.execution import execute_tool_calls
from uni_tool.core.models import Prefix, Tag, ToolCall

"""
中间件场景示例 (Middleware Scenarios)

展示如何结合使用多个 Middleware 和 ToolExpression (Tag, Prefix, And, Or, Not)
来构建复杂的控制逻辑（Scenario）。

场景设定：
1. 全局审计 (Audit): 所有工具调用都记录日志。
2. 权限控制 (Auth): 只有带有 "admin" 标签或名称以 "admin_" 开头的工具需要管理员权限。
3. 外部计费 (Billing): 只有带有 "external" 标签的工具需要计费检查。
"""


universe = Universe()


# 1. 定义工具 (Tools)
@universe.tool(name="admin_delete_user", tags={"admin", "critical"})
def admin_delete_user(user_id: str) -> str:
    return f"User {user_id} deleted."


@universe.tool(name="admin_list_users", tags={"admin", "read_only"})
def admin_list_users() -> list:
    return ["alice", "bob"]


@universe.tool(name="public_echo", tags={"public"})
def public_echo(msg: str) -> str:
    return f"Echo: {msg}"


@universe.tool(name="external_search", tags={"external"})
def external_search(query: str) -> str:
    return f"Results for {query}"


@universe.tool(name="internal_process", tags={"internal"})
def internal_process() -> str:
    return "Processed internally"


# 2. 定义中间件 (Middlewares)


class AuditMiddleware:
    """记录所有调用的审计日志"""

    async def __call__(self, call: ToolCall, next_handler) -> Any:
        print(f"📝 [Audit] Start: {call.name}")
        try:
            result = await next_handler(call)
            print(f"📝 [Audit] Success: {call.name}")
            return result
        except Exception as e:
            print(f"📝 [Audit] Failed: {call.name} - {e}")
            raise


class AuthMiddleware:
    """检查管理员权限"""

    async def __call__(self, call: ToolCall, next_handler) -> Any:
        print(f"🔒 [Auth] Checking permissions for {call.name}...")
        role = call.context.get("role", "guest")
        if role != "admin":
            raise PermissionError(f"Access denied: User with role '{role}' cannot access restricted tool.")
        return await next_handler(call)


class BillingMiddleware:
    """模拟外部调用的计费检查"""

    async def __call__(self, call: ToolCall, next_handler) -> Any:
        print(f"💰 [Billing] Calculating cost for {call.name}...")
        # 模拟：检查余额等逻辑
        return await next_handler(call)


# 3. 注册中间件与范围 (Registration with Scopes)

# Scenario 1: 全局审计
# Scope: None (Global)
universe.use(AuditMiddleware())

# Scenario 2: 管理员权限控制
# Scope: (Tag("admin") OR Prefix("admin_")) AND NOT Tag("read_only")
# 逻辑：标记为 admin 或者以 admin_ 开头，且非 read_only 的工具需要鉴权
# (注：这里故意设计复杂一点，假设 read_only 的 admin 工具不需要强鉴权，仅作演示 Expression 组合)
# 修正逻辑：通常 admin 工具都需要鉴权，这里演示简单逻辑： Tag("admin") OR Prefix("admin_")
admin_scope = Tag("admin") | Prefix("admin_")
universe.use(AuthMiddleware(), scope=admin_scope)

# Scenario 3: 外部计费
# Scope: Tag("external")
universe.use(BillingMiddleware(), scope=Tag("external"))


# 4. 执行测试 (Execution)
async def main():
    print("=== 07 Middleware Scenarios ===")

    # Case 1: Admin 调用 admin 工具 (Tag="admin")
    # 预期: Audit ✅, Auth ✅ (Pass), Billing ❌ (Skip)
    print("\n--- Case 1: Admin calling admin_delete_user ---")
    call1 = ToolCall(id="c1", name="admin_delete_user", arguments={"user_id": "u1"}, context={"role": "admin"})
    await execute_tool_calls(universe, [call1])

    # Case 2: Guest 调用 admin 工具
    # 预期: Audit ✅, Auth ❌ (Fail), Billing ❌ (Skip)
    print("\n--- Case 2: Guest calling admin_delete_user ---")
    call2 = ToolCall(id="c2", name="admin_delete_user", arguments={"user_id": "u2"}, context={"role": "guest"})
    results = await execute_tool_calls(universe, [call2])
    if results[0].error:
        print(f"❌ Error caught as expected: {results[0].error}")

    # Case 3: Guest 调用 public 工具
    # 预期: Audit ✅, Auth ❌ (Skip), Billing ❌ (Skip)
    print("\n--- Case 3: Guest calling public_echo ---")
    call3 = ToolCall(id="c3", name="public_echo", arguments={"msg": "hello"}, context={"role": "guest"})
    await execute_tool_calls(universe, [call3])

    # Case 4: User 调用 external 工具
    # 预期: Audit ✅, Auth ❌ (Skip), Billing ✅ (Pass)
    print("\n--- Case 4: Calling external_search ---")
    call4 = ToolCall(id="c4", name="external_search", arguments={"query": "python"}, context={"role": "guest"})
    await execute_tool_calls(universe, [call4])


if __name__ == "__main__":
    asyncio.run(main())
