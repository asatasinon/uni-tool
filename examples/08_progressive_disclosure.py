"""
UniTools SDK - 渐进式披露 (Progressive Disclosure) 示例

展示如何使用 SDK 实现层级式导航 (Hierarchical Navigation) 和复杂的权限控制。
原理：
1. 利用 tags 将工具分类 (root, finance, ops, admin, read, common)。
2. 使用 DSL 字符串表达式定义复杂的上下文过滤规则。
3. 展示不同模式下的工具可见性差异。

DSL 语法：
- `|` : OR 运算符
- `&` : AND 运算符
- `~` : NOT 运算符
- `()` : 分组
- `tag:name` : 标签匹配 (可省略 tag: 前缀)
- `prefix:xxx` : 名称前缀匹配
- `name:xxx` : 名称精确匹配
- `^xxx` : prefix:xxx 的简写
- `` `xxx` `` : name:xxx 的简写
"""

import asyncio

from uni_tool import universe

# =============================================================================
# 1. 定义状态管理 (模拟会话上下文)
# =============================================================================


class SessionContext:
    def __init__(self):
        self.current_mode = "root"
        # 预定义模式到 DSL 过滤表达式的映射
        # 演示复杂的过滤场景：
        # - 分级权限: finance_admin (可读写) vs finance_read (只读)
        # - 跨域组合: devops (ops + debug/admin)
        # - 公共工具: common 标签在多数模式下可见
        self.mode_configs: dict[str, str] = {
            # Root 模式：只显示 root 导航和公共工具
            "root": "root | common",
            # Finance Admin: 显示所有 finance 工具和公共工具
            "finance_admin": "finance | common",
            # Finance Read: 只显示 finance 且标记为 read 的工具，以及公共工具
            "finance_read": "(finance & read) | common",
            # Ops Safe: 显示 ops 且 read 的工具，排除 admin 工具（演示 NOT）
            # 注意：ops & read 已经限定了范围，再排除 admin 只是双重保险或用于演示
            "ops_safe": "(ops & read & ~admin) | common",
            # DevOps: 显示 ops 所有工具，加上 root 导航（方便切换）
            "devops": "ops | root | common",
            # Navigation Only: 仅显示名称以 enter_ 开头的导航工具与公共工具（演示前缀匹配）
            "nav_only": "^enter_ | common",
        }

    def set_mode(self, mode: str):
        if mode not in self.mode_configs:
            raise ValueError(f"Unknown mode: {mode}")
        print(f"\n[System] Switching context: {self.current_mode} -> {mode}")
        self.current_mode = mode

    @property
    def current_filter(self) -> str:
        """返回当前模式的 DSL 过滤表达式."""
        return self.mode_configs[self.current_mode]


# 全局上下文实例
context = SessionContext()

# =============================================================================
# 2. 定义工具集
# =============================================================================

# --- Root 层级工具 ---


@universe.tool(tags={"root"})
def enter_finance_admin() -> str:
    """Enter finance admin mode (full access)."""
    context.set_mode("finance_admin")
    return "Entered Finance Admin Mode."


@universe.tool(tags={"root"})
def enter_finance_read() -> str:
    """Enter finance read-only mode."""
    context.set_mode("finance_read")
    return "Entered Finance Read-Only Mode."


@universe.tool(tags={"root"})
def enter_ops_safe() -> str:
    """Enter safe operations mode."""
    context.set_mode("ops_safe")
    return "Entered Ops Safe Mode."


@universe.tool(tags={"root"})
def enter_devops() -> str:
    """Enter DevOps mode (full ops access)."""
    context.set_mode("devops")
    return "Entered DevOps Mode."


@universe.tool(tags={"root"})
def enter_navigation_only() -> str:
    """Enter navigation-only mode (prefix matching)."""
    context.set_mode("nav_only")
    return "Entered Navigation-Only Mode."


# --- Finance 层级工具 ---


@universe.tool(tags={"finance", "read"})
def check_balance(account_id: str) -> str:
    """Check account balance (Read-Only)."""
    return f"Balance for {account_id}: $1,000,000"


@universe.tool(tags={"finance", "admin"})
def transfer_money(to_account: str, amount: float) -> str:
    """Transfer money (Admin only)."""
    return f"Transferred ${amount} to {to_account}."


# --- Ops 层级工具 ---


@universe.tool(tags={"ops", "admin"})
def restart_server(server_name: str) -> str:
    """Restart a specific server (Admin only)."""
    return f"Server {server_name} is restarting..."


@universe.tool(tags={"ops", "read"})
def check_logs(server_name: str, lines: int = 10) -> str:
    """Check server logs (Read-Only)."""
    return f"Last {lines} lines of logs from {server_name}..."


# --- Common 工具 ---


@universe.tool(tags={"common"})
def help() -> str:
    """Get help information."""
    return "Available commands depend on your current mode."


@universe.tool(tags={"common"})
def back_to_root() -> str:
    """Return to root menu."""
    context.set_mode("root")
    return "Returned to root menu."


# =============================================================================
# 3. 模拟 LLM 交互循环
# =============================================================================


async def main():
    print("=" * 60)
    print("UniTools SDK - Advanced Progressive Disclosure Demo")
    print("=" * 60)

    # 模拟用户的一系列请求
    user_requests = [
        # 1. 初始状态 (root)
        "System: Start",
        # 2. 进入 Finance Read-Only 模式
        {
            "tool_calls": [
                {"id": "call_1", "type": "function", "function": {"name": "enter_finance_read", "arguments": "{}"}}
            ]
        },
        # 3. 尝试查询余额 (允许)
        {
            "tool_calls": [
                {
                    "id": "call_2",
                    "type": "function",
                    "function": {"name": "check_balance", "arguments": '{"account_id": "acc_123"}'},
                }
            ]
        },
        # 4. 尝试转账 (应该失败，因为当前模式是 finance_read)
        # 注意：正常情况下 LLM 不会看到这个工具，但如果它产生幻觉强行调用，tool_filter 应该拦截它
        {
            "tool_calls": [
                {
                    "id": "call_3",
                    "type": "function",
                    "function": {"name": "transfer_money", "arguments": '{"to_account": "bob", "amount": 100}'},
                }
            ]
        },
        # 5. 返回 Root
        {"tool_calls": [{"id": "call_4", "type": "function", "function": {"name": "back_to_root", "arguments": "{}"}}]},
        # 6. 进入 Navigation Only 模式（演示前缀匹配）
        {
            "tool_calls": [
                {"id": "call_5", "type": "function", "function": {"name": "enter_navigation_only", "arguments": "{}"}}
            ]
        },
        # 7. 查看当前可见导航工具
        "System: Inspect navigation-only tools",
        # 8. 进入 DevOps 模式 (Full Ops)
        {"tool_calls": [{"id": "call_6", "type": "function", "function": {"name": "enter_devops", "arguments": "{}"}}]},
        # 9. 重启服务器 (允许)
        {
            "tool_calls": [
                {
                    "id": "call_7",
                    "type": "function",
                    "function": {"name": "restart_server", "arguments": '{"server_name": "prod-db"}'},
                }
            ]
        },
    ]

    for step, request in enumerate(user_requests):
        print(f"\n--- Step {step + 1} ---")

        # 1. 根据当前 mode 获取可见工具 (使用 DSL 字符串)
        current_filter = context.current_filter
        visible_tools = universe[current_filter].tools

        print(f"Current Context: [{context.current_mode}]")
        print(f"Filter DSL: {current_filter}")
        print(f"Visible Tools: {[t.name for t in visible_tools]}")

        # 如果是字符串，仅打印模拟的用户意图
        if isinstance(request, str):
            print(f"User Input: {request}")
            continue

        # 2. 模拟 LLM 处理
        print("LLM simulates tool call...")

        id_to_name = {}
        if isinstance(request, dict) and "tool_calls" in request:
            for call in request["tool_calls"]:
                id_to_name[call["id"]] = call["function"]["name"]

        # 3. 执行工具
        # 关键：使用 DSL 表达式进行运行时安全检查
        # universe[current_filter] 解析 DSL 字符串并返回 ToolSet
        results = await universe.dispatch(
            request,
            tool_filter=universe[current_filter].expression,
        )

        for r in results:
            status = "SUCCESS" if r.is_success else "DENIED/FAILED"
            func_name = id_to_name.get(r.id, "Unknown")
            print(f"Execution: {func_name} -> {status}")
            if r.is_success:
                print(f"Result: {r.result}")
            else:
                print(f"Error: {r.error}")


if __name__ == "__main__":
    asyncio.run(main())
