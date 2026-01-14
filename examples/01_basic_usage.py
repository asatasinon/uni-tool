"""
基础用法示例 (Basic Usage)

展示如何创建一个 Universe，注册一个简单的工具，并手动执行它。
"""

import asyncio
from uni_tool import Universe
from uni_tool.core.models import ToolCall
from uni_tool.core.execution import execute_tool_calls

# 1. 创建 Universe 实例
# Universe 是工具注册和执行的核心容器
universe = Universe()


# 2. 注册工具
# 使用 @universe.tool 装饰器将函数注册为工具
@universe.tool(name="calculator_add", tags={"math"})
def add(a: int, b: int) -> int:
    """
    Add two numbers together.

    Args:
        a: The first number.
        b: The second number.
    """
    return a + b


async def main():
    print("=== 01 Basic Usage ===")

    # 3. 构造工具调用
    # 在实际场景中，这个 ToolCall 通常由 Driver 解析 LLM 的响应生成
    call = ToolCall(id="call_1", name="calculator_add", arguments={"a": 5, "b": 3})

    print(f"Executing tool: {call.name} with args: {call.arguments}")

    # 4. 执行工具
    # 使用 core.execution.execute_tool_calls 执行一组调用
    results = await execute_tool_calls(universe, [call])

    for res in results:
        if res.error:
            print(f"Error: {res.error}")
        else:
            print(f"Result: {res.result}")  # Expected: 8


if __name__ == "__main__":
    asyncio.run(main())
