"""
依赖注入示例 (Dependency Injection)

展示如何使用 Injected 模式将上下文（如 User ID）注入到工具中，
而不需要 LLM 显式提供这些参数。这对于安全性和简化 Prompt 非常重要。
"""

import asyncio
from typing import Annotated
from uni_tool import Universe, Injected
from uni_tool.core.models import ToolCall
from uni_tool.core.execution import execute_tool_calls

universe = Universe()


# 1. 定义带注入参数的工具
# user_id 参数被标记为 Injected("uid")
# 这意味着它的值将从 context["uid"] 中获取，而不是从 LLM 的 arguments 中获取
@universe.tool(name="get_user_profile")
def get_user_profile(query: str, user_id: Annotated[str, Injected("uid")]) -> str:
    """
    Get profile information for the current user.

    Args:
        query: What to look for.
        user_id: The authenticated user ID (injected).
    """
    return f"Profile for user {user_id}: matches query '{query}'"


async def main():
    print("=== 04 Dependency Injection ===")

    # 2. 准备上下文
    # 在实际应用中，这里可能包含来自 HTTP 请求的鉴权信息
    context = {"uid": "u_12345"}

    # 3. 构造调用
    # 注意：arguments 中只有 'query'，没有 'user_id'
    # 'user_id' 将在执行时由框架自动注入
    call = ToolCall(
        id="call_1",
        name="get_user_profile",
        arguments={"query": "email"},
        context=context,  # 传入上下文
    )

    result = await execute_tool_calls(universe, [call])
    print(f"Result: {result[0].result}")

    # Case 2: 缺少上下文引发错误
    print("\n--- Testing missing context ---")
    call_missing = ToolCall(
        id="call_2",
        name="get_user_profile",
        arguments={"query": "email"},
        context={},  # 空上下文
    )
    res_missing = await execute_tool_calls(universe, [call_missing])
    print(f"Error: {res_missing[0].error}")


if __name__ == "__main__":
    asyncio.run(main())
