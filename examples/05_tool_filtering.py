"""
UniTools SDK - 工具过滤示例

展示如何使用 ToolExpression 进行复杂的工具过滤：
- Tag: 按标签过滤
- Prefix: 按前缀过滤
- ToolName: 按名称精确匹配
- And, Or, Not: 组合表达式
- tool_filter: 在 dispatch 时限制可执行的工具
"""

import asyncio

from uni_tool import (
    universe,
    Tag,
    Prefix,
    ToolName,
    And,
    Or,
    Not,
)


# =============================================================================
# 1. 注册多种类型的工具
# =============================================================================


@universe.tool(tags={"api", "v1", "read"})
def api_v1_get_users() -> list:
    """Get all users (API v1, read-only)."""
    return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


@universe.tool(tags={"api", "v1", "write"})
def api_v1_create_user(name: str) -> dict:
    """Create a new user (API v1, write).

    Args:
        name: User name.
    """
    return {"id": 3, "name": name, "created": True}


@universe.tool(tags={"api", "v2", "read"})
def api_v2_get_users(include_inactive: bool = False) -> list:
    """Get users with v2 format.

    Args:
        include_inactive: Include inactive users.
    """
    users = [{"id": 1, "name": "Alice", "active": True}]
    if include_inactive:
        users.append({"id": 2, "name": "Bob", "active": False})
    return users


@universe.tool(tags={"internal", "admin"})
def admin_reset_cache() -> dict:
    """Reset system cache (admin only)."""
    return {"status": "cache_cleared"}


@universe.tool(tags={"internal", "debug"})
def debug_dump_state() -> dict:
    """Dump internal state (debug only)."""
    return {"state": "dumped", "items": 42}


@universe.tool(tags={"public"})
def get_server_time() -> str:
    """Get current server time (public)."""
    from datetime import datetime

    return datetime.now().isoformat()


# =============================================================================
# 2. 演示各种过滤表达式
# =============================================================================


async def main():
    print("=" * 60)
    print("UniTools SDK - Tool Filtering Demo")
    print("=" * 60)

    # --- 基础标签过滤 ---
    print("\n[1] Basic Tag filtering:")

    api_tools = universe[Tag("api")].tools
    print(f"  Tag('api'): {[t.name for t in api_tools]}")

    v1_tools = universe[Tag("v1")].tools
    print(f"  Tag('v1'): {[t.name for t in v1_tools]}")

    # --- 组合表达式: AND ---
    print("\n[2] AND expression (Tag('api') & Tag('read')):")
    read_api_tools = universe[Tag("api") & Tag("read")].tools
    print(f"  Result: {[t.name for t in read_api_tools]}")

    # --- 组合表达式: OR ---
    print("\n[3] OR expression (Tag('admin') | Tag('public')):")
    admin_or_public = universe[Tag("admin") | Tag("public")].tools
    print(f"  Result: {[t.name for t in admin_or_public]}")

    # --- 组合表达式: NOT ---
    print("\n[4] NOT expression (~Tag('internal')):")
    non_internal = universe[~Tag("internal")].tools
    print(f"  Result: {[t.name for t in non_internal]}")

    # --- 复杂组合 ---
    print("\n[5] Complex: (Tag('api') & Tag('v1')) | Tag('public'):")
    complex_filter = (Tag("api") & Tag("v1")) | Tag("public")
    complex_tools = universe[complex_filter].tools
    print(f"  Result: {[t.name for t in complex_tools]}")

    # --- Prefix 过滤 ---
    print("\n[6] Prefix filtering:")
    api_v1_prefix = universe[Prefix("api_v1_")].tools
    print(f"  Prefix('api_v1_'): {[t.name for t in api_v1_prefix]}")

    # --- ToolName 精确匹配 ---
    print("\n[7] Exact name matching:")
    exact_match = universe[ToolName("get_server_time")].tools
    print(f"  ToolName('get_server_time'): {[t.name for t in exact_match]}")

    # --- 使用等价类 ---
    print("\n[8] Using And/Or/Not classes directly:")

    # And class
    and_result = universe[And(Tag("api"), Tag("write"))].tools
    print(f"  And(Tag('api'), Tag('write')): {[t.name for t in and_result]}")

    # Or class
    or_result = universe[Or(Tag("debug"), Tag("admin"))].tools
    print(f"  Or(Tag('debug'), Tag('admin')): {[t.name for t in or_result]}")

    # Not class
    not_result = universe[Not(Tag("api"))].tools
    print(f"  Not(Tag('api')): {[t.name for t in not_result]}")

    # ==========================================================================
    # 3. 在 dispatch 时使用 tool_filter
    # ==========================================================================
    print("\n" + "=" * 60)
    print("Dispatch with tool_filter")
    print("=" * 60)

    # 模拟 LLM 尝试调用多种工具
    llm_response = {
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "api_v1_get_users", "arguments": "{}"},
            },
            {
                "id": "call_2",
                "type": "function",
                "function": {"name": "admin_reset_cache", "arguments": "{}"},
            },
            {
                "id": "call_3",
                "type": "function",
                "function": {"name": "get_server_time", "arguments": "{}"},
            },
        ]
    }

    # --- 场景 1: 只允许 read 操作 ---
    print("\n[Scenario 1] Only allow 'read' tagged tools:")
    results1 = await universe.dispatch(
        llm_response,
        tool_filter=Tag("read"),
    )
    for r in results1:
        status = "ALLOWED" if r.is_success else "DENIED"
        print(f"  {r.id}: {status}")
        if not r.is_success:
            print(f"    Reason: {r.error}")

    # --- 场景 2: 禁止 internal 工具 ---
    print("\n[Scenario 2] Deny 'internal' tagged tools:")
    results2 = await universe.dispatch(
        llm_response,
        tool_filter=~Tag("internal"),
    )
    for r in results2:
        status = "ALLOWED" if r.is_success else "DENIED"
        print(f"  {r.id}: {status}")

    # --- 场景 3: 只允许特定工具名 ---
    print("\n[Scenario 3] Only allow specific tool by name:")
    results3 = await universe.dispatch(
        llm_response,
        tool_filter=ToolName("get_server_time"),
    )
    for r in results3:
        status = "ALLOWED" if r.is_success else "DENIED"
        print(f"  {r.id}: {status}")
        if r.is_success:
            print(f"    Result: {r.result}")

    # --- 场景 4: 复杂过滤条件 ---
    print("\n[Scenario 4] Complex filter: (read OR public) AND NOT internal:")
    complex_filter = (Tag("read") | Tag("public")) & ~Tag("internal")
    results4 = await universe.dispatch(
        llm_response,
        tool_filter=complex_filter,
    )
    for r in results4:
        status = "ALLOWED" if r.is_success else "DENIED"
        detail = r.result if r.is_success else r.error[:50]
        print(f"  {r.id}: {status} -> {detail}")

    # ==========================================================================
    # 4. 渲染过滤后的 schema
    # ==========================================================================
    print("\n" + "=" * 60)
    print("Render filtered schema for LLM")
    print("=" * 60)

    # 只发送 read-only API 工具给 LLM
    print("\n[Render] Only 'read' API tools for LLM:")
    read_schema = universe[Tag("api") & Tag("read")].render("openai")
    for tool in read_schema:
        print(f"  - {tool['function']['name']}: {tool['function']['description'][:50]}...")


if __name__ == "__main__":
    asyncio.run(main())
