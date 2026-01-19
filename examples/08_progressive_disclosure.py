"""
UniTools SDK - 渐进式披露 (Progressive Disclosure) 示例

展示如何使用 SDK 实现层级式导航 (Hierarchical Navigation)。
原理：
1. 利用 tags 将工具分类 (root, finance, ops)。
2. 根据当前上下文动态过滤展示给 LLM 的工具。
3. 通过调用导航工具切换上下文。
"""

import asyncio

from uni_tool import Tag, universe

# =============================================================================
# 1. 定义状态管理 (模拟会话上下文)
# =============================================================================


class SessionContext:
    def __init__(self):
        self.current_mode = "root"

    def set_mode(self, mode: str):
        print(f"\n[System] Switching context: {self.current_mode} -> {mode}")
        self.current_mode = mode


# 全局上下文实例
context = SessionContext()

# =============================================================================
# 2. 定义工具集
# =============================================================================

# --- Root 层级工具 ---


@universe.tool(tags={"root"})
def enter_finance_mode() -> str:
    """Enter finance mode to access financial tools.

    Use this when user asks for money transfer, balance check, etc.
    """
    context.set_mode("finance")
    return "Entered finance mode. You can now use financial tools."


@universe.tool(tags={"root"})
def enter_ops_mode() -> str:
    """Enter operations mode to access server management tools.

    Use this when user asks for server restart, logs, etc.
    """
    context.set_mode("ops")
    return "Entered operations mode. You can now use operations tools."


# --- Finance 层级工具 ---


@universe.tool(tags={"finance"})
def check_balance(account_id: str) -> str:
    """Check account balance.

    Args:
        account_id: The account ID to check.
    """
    return f"Balance for {account_id}: $1,000,000"


@universe.tool(tags={"finance"})
def transfer_money(to_account: str, amount: float) -> str:
    """Transfer money to another account.

    Args:
        to_account: The recipient account ID.
        amount: Amount to transfer.
    """
    return f"Transferred ${amount} to {to_account}."


# --- Ops 层级工具 ---


@universe.tool(tags={"ops"})
def restart_server(server_name: str) -> str:
    """Restart a specific server.

    Args:
        server_name: Name of the server to restart.
    """
    return f"Server {server_name} is restarting..."


@universe.tool(tags={"ops"})
def check_logs(server_name: str, lines: int = 10) -> str:
    """Check server logs.

    Args:
        server_name: Name of the server.
        lines: Number of lines to read.
    """
    return f"Last {lines} lines of logs from {server_name}..."


# --- 通用导航工具 ---


@universe.tool(tags={"finance", "ops"})
def back_to_main_menu() -> str:
    """Return to the main menu (root)."""
    context.set_mode("root")
    return "Returned to main menu."


# =============================================================================
# 3. 模拟 LLM 交互循环
# =============================================================================


async def main():
    print("=" * 60)
    print("UniTools SDK - Hierarchical Navigation Demo")
    print("=" * 60)

    # 模拟用户的一系列请求
    user_requests = [
        # 1. 初始状态 (root)
        "System: Start",
        # 2. 用户想转账 -> LLM 应该调用 enter_finance_mode
        {
            "tool_calls": [
                {"id": "call_1", "type": "function", "function": {"name": "enter_finance_mode", "arguments": "{}"}}
            ]
        },
        # 3. 进入 finance 模式后 -> LLM 调用 check_balance
        {
            "tool_calls": [
                {
                    "id": "call_2",
                    "type": "function",
                    "function": {"name": "check_balance", "arguments": '{"account_id": "acc_123"}'},
                }
            ]
        },
        # 4. 用户想重启服务器 -> LLM 需要先退出或直接切换?
        # 在这个简单模型中，通常需要先返回 root 或直接允许切换（取决于 Tag 设计）。
        # 这里演示先返回 root。
        {
            "tool_calls": [
                {"id": "call_3", "type": "function", "function": {"name": "back_to_main_menu", "arguments": "{}"}}
            ]
        },
        # 5. 回到 root -> 进入 ops
        {
            "tool_calls": [
                {"id": "call_4", "type": "function", "function": {"name": "enter_ops_mode", "arguments": "{}"}}
            ]
        },
    ]

    for step, request in enumerate(user_requests):
        print(f"\n--- Step {step + 1} ---")

        # 1. 根据当前 mode 获取可见工具
        current_tag = Tag(context.current_mode)
        visible_tools = universe[current_tag].tools

        print(f"Current Context: [{context.current_mode}]")
        print(f"Visible Tools: {[t.name for t in visible_tools]}")

        # 如果是字符串，仅打印模拟的用户意图
        if isinstance(request, str):
            print(f"User Input: {request}")
            continue

        # 2. 模拟 LLM 处理 (这里直接使用预定义的 tool_calls)
        print("LLM simulates tool call...")

        # 建立 ID 到函数名的映射，以便后续打印
        id_to_name = {}
        if isinstance(request, dict) and "tool_calls" in request:
            for call in request["tool_calls"]:
                id_to_name[call["id"]] = call["function"]["name"]

        # 3. 执行工具
        # 注意：在实际应用中，这里应该将 visible_tools 渲染给 LLM
        # universe[current_tag].render("openai")

        # 安全检查：确保 LLM 调用的工具在当前上下文是允许的
        # 使用 dispatch 的 tool_filter 参数进行运行时强制检查
        results = await universe.dispatch(
            request,
            tool_filter=current_tag,  # 关键：强制只允许调用当前 tag 下的工具
        )

        for r in results:
            status = "SUCCESS" if r.is_success else "FAILED"
            func_name = id_to_name.get(r.id, "Unknown")
            print(f"Execution: {func_name} -> {status}")
            print(f"Result: {r.result}")
            if not r.is_success:
                print(f"Error: {r.error}")


if __name__ == "__main__":
    asyncio.run(main())
