"""
全特性综合示例 (All-In-One Showcase)

这个示例演示了 uni-tool 的所有核心特性在一个复杂的企业级场景中的协同工作：

1. **工具定义 (Tool Definitions)**:
   - 使用 `@universe.tool` 注册独立函数。
   - 使用 `@universe.bind` 注册类方法。
   - 使用 `Tags` 进行分类 (system, user, admin, report)。

2. **依赖注入 (Dependency Injection)**:
   - 使用 `Annotated[T, Injected("key")]` 注入上下文信息（如当前用户、请求ID）。

3. **中间件与作用域 (Middleware & Scopes)**:
   - **全局中间件**: 结构化日志记录。
   - **作用域中间件**:
     - 鉴权 (Auth): 仅应用于敏感操作 (`admin` 标签 或 `write` 标签)。
     - 性能监控 (Monitor): 仅应用于耗时操作 (`heavy` 标签)。

4. **工具过滤与视图 (Filtering & Views)**:
   - 为不同角色（普通用户 vs 管理员）生成不同的工具 Schema。

5. **驱动集成 (Driver Integration)**:
   - 使用 `OpenAIDriver` 生成 Schema 和解析响应。

6. **执行流程 (Execution Flow)**:
   - 模拟完整的 "Prompt -> Schema -> LLM -> Tool Call -> Execution" 循环。
"""

import asyncio
import json
import logging
import time
from typing import Annotated, Any, Dict

from uni_tool import Injected, Universe
from uni_tool.core.execution import execute_tool_calls
from uni_tool.core.models import Tag, ToolCall
from uni_tool.drivers.openai import OpenAIDriver

# --- 0. Setup ---
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("all-in-one")

universe = Universe()
driver = OpenAIDriver()

# --- 1. Define Tools (工具定义) ---


# 1.1 类绑定：系统基础工具
@universe.bind(prefix="sys_", tags={"system", "common"})
class SystemTools:
    def version(self) -> str:
        """Get system version."""
        return "v2.0.0"

    def time(self) -> str:
        """Get server time."""
        return time.strftime("%X")


# 1.2 普通函数：用户操作
@universe.tool(name="user_get_profile", tags={"user", "read"})
def user_get_profile(user_id: Annotated[str, Injected("current_user_id")]) -> Dict[str, Any]:
    """Get current user's profile."""
    return {"id": user_id, "name": "Alice", "role": "user"}


@universe.tool(name="user_update_settings", tags={"user", "write"})
def user_update_settings(settings: Dict[str, Any], user_id: Annotated[str, Injected("current_user_id")]) -> str:
    """Update user settings."""
    return f"Settings updated for {user_id}: {settings}"


# 1.3 普通函数：管理员操作 (敏感)
@universe.tool(name="admin_delete_user", tags={"admin", "critical"})
def admin_delete_user(target_user_id: str, admin_id: Annotated[str, Injected("current_user_id")]) -> str:
    """Delete a user (Admin only)."""
    print(f"  [Implementation] Admin {admin_id} deleting {target_user_id}...")
    return f"User {target_user_id} deleted by {admin_id}"


# 1.4 普通函数：报表生成 (耗时操作)
@universe.tool(name="report_generate_monthly", tags={"report", "heavy", "read"})
def report_generate_monthly(month: str) -> str:
    """Generate heavy monthly report."""
    # Simulate heavy work
    time.sleep(0.1)
    return f"Report for {month} generated (15MB)"


# --- 2. Define Middlewares (中间件定义) ---


class StructuredLogger:
    """Global: Log start/end of every tool."""

    async def __call__(self, call: ToolCall, next_handler) -> Any:
        print(f"📝 [Log] Invoke: {call.name} (ID: {call.id})")
        try:
            res = await next_handler(call)
            print(f"📝 [Log] Success: {call.name}")
            return res
        except Exception as e:
            print(f"📝 [Log] Error: {call.name} -> {e}")
            raise


class AuthGuard:
    """Scoped: Check permissions for sensitive tools."""

    async def __call__(self, call: ToolCall, next_handler) -> Any:
        user_role = call.context.get("user_role", "guest")
        print(f"🔒 [Auth] Checking {call.name} for role '{user_role}'...")

        # Simple RBAC logic
        if "admin" in call.context.get("required_scopes", []):
            if user_role != "admin":
                raise PermissionError("Require ADMIN role")

        # For demo: if tool tag has 'admin', require admin role
        # We can inspect tool metadata if we had access, but here we rely on the fact
        # that this middleware is ONLY applied to sensitive tools via Universe registration.
        # So we just check if the user is allowed to do "sensitive" things.

        if user_role == "guest":
            raise PermissionError("Guests cannot perform sensitive actions")

        if user_role != "admin" and "admin_" in call.name:
            raise PermissionError("Only admins can call admin_* tools")

        return await next_handler(call)


class PerformanceMonitor:
    """Scoped: Monitor heavy tools."""

    async def __call__(self, call: ToolCall, next_handler) -> Any:
        start = time.perf_counter()
        print(f"⏱️ [Perf] Monitoring {call.name}...")
        res = await next_handler(call)
        duration = (time.perf_counter() - start) * 1000
        print(f"⏱️ [Perf] {call.name} took {duration:.2f}ms")
        return res


# --- 3. Registration & Configuration (注册与配置) ---

# 3.1 Global Middleware
universe.use(StructuredLogger())

# 3.2 Scoped Middleware: Auth
# Apply Auth to: Tools tagged "admin" OR "critical" OR "write"
# Expression: Tag("admin") | Tag("critical") | Tag("write")
auth_scope = Tag("admin") | Tag("critical") | Tag("write")
universe.use(AuthGuard(), scope=auth_scope)

# 3.3 Scoped Middleware: Perf
# Apply Perf to: Tools tagged "heavy"
universe.use(PerformanceMonitor(), scope=Tag("heavy"))

# --- 4. Scenarios (场景演示) ---


async def simulate_user_session():
    print("\n\n=== Scenario 1: Regular User Session ===")

    # Context injected by the application (e.g., API Gateway)
    user_context = {"current_user_id": "u_alice", "user_role": "user"}

    # 4.1 Filter Tools: Users should not see admin tools
    # View: (Tag("user") | Tag("common") | Tag("report")) AND NOT Tag("admin")
    user_view_expr = (Tag("user") | Tag("common") | Tag("report")) & ~Tag("admin")
    user_view = universe[user_view_expr]

    print(f"Tools available to User: {[t.name for t in user_view.get_tools()]}")

    # 4.2 Generate Schema for User
    schema = user_view.render("openai")
    print("Generated Tools Schema:")
    print(json.dumps(schema, indent=2))

    # 4.3 Simulate LLM interaction
    # User asks: "Update my settings to dark mode and get my profile"
    print("User: 'Update settings to dark mode'")

    mock_llm_resp = {
        "tool_calls": [
            {
                "id": "call_u1",
                "type": "function",
                "function": {"name": "user_update_settings", "arguments": json.dumps({"settings": {"theme": "dark"}})},
            }
        ]
    }

    # 4.4 Parse & Inject Context
    calls = driver.parse(mock_llm_resp)
    for call in calls:
        call.context.update(user_context)

    # 4.5 Execute
    # AuthGuard will run because 'user_update_settings' has Tag('write')
    results = await execute_tool_calls(universe, calls)
    print(f"Result: {results[0].result}")


async def simulate_admin_session():
    print("\n\n=== Scenario 2: Admin Session ===")

    admin_context = {"current_user_id": "u_admin_bob", "user_role": "admin"}

    # Admin sees everything
    admin_view = universe[Tag("admin")]
    print(f"Tools available to Admin: {[t.name for t in admin_view.get_tools()]}")

    # Admin performs critical action
    print("Admin: 'Delete user u_malicious'")

    mock_llm_resp = {
        "tool_calls": [
            {
                "id": "call_a1",
                "type": "function",
                "function": {"name": "admin_delete_user", "arguments": json.dumps({"target_user_id": "u_malicious"})},
            }
        ]
    }

    calls = driver.parse(mock_llm_resp)
    for call in calls:
        call.context.update(admin_context)

    # Execute: Should pass AuthGuard
    results = await execute_tool_calls(universe, calls)
    print(f"Result: {results[0].result}")


async def simulate_attack():
    print("\n\n=== Scenario 3: Unauthorized Access Attempt ===")

    attacker_context = {
        "current_user_id": "u_attacker",
        "user_role": "user",  # Not admin
    }

    # Attacker tries to guess the tool name "admin_delete_user"
    # even if it wasn't in their schema (Prompt Injection or specialized client)
    print("Attacker: (Directly calls 'admin_delete_user')")

    attack_call = ToolCall(
        id="call_hack", name="admin_delete_user", arguments={"target_user_id": "u_victim"}, context=attacker_context
    )

    # Execute
    results = await execute_tool_calls(universe, [attack_call])

    if results[0].error:
        print(f"🛡️ Attack Blocked: {results[0].error}")
    else:
        print(f"⚠️ Attack Succeeded: {results[0].result}")


async def simulate_heavy_task():
    print("\n\n=== Scenario 4: Heavy Task Monitoring ===")

    context = {"current_user_id": "u_analyst", "user_role": "user"}

    call = ToolCall(id="call_perf", name="report_generate_monthly", arguments={"month": "2023-10"}, context=context)

    # Should trigger PerformanceMonitor because of Tag("heavy")
    # Should NOT trigger AuthGuard (Tag("read") is not in auth_scope: admin|critical|write)
    # Wait, 'report' is read-only, but verify tags: report_generate_monthly has 'read', 'heavy', 'report'.
    # auth_scope is 'admin'|'critical'|'write'. So AuthGuard is SKIPPED.

    await execute_tool_calls(universe, [call])


async def main():
    await simulate_user_session()
    await simulate_admin_session()
    await simulate_attack()
    await simulate_heavy_task()


if __name__ == "__main__":
    asyncio.run(main())
