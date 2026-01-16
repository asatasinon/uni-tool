"""
UniTools SDK - 最小使用示例

展示最基础的工具注册和执行流程。
"""

import asyncio
from uni_tool import universe


# 1. 注册一个简单的工具
@universe.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: First number.
        b: Second number.
    """
    return a + b


async def main():
    # 2. 渲染工具 schema（用于发送给 LLM）
    schema = universe.render("openai")
    print("Tool Schema for LLM:")
    print(schema)

    # 3. 模拟 LLM 返回的 tool_call 响应
    llm_response = {
        "tool_calls": [
            {
                "id": "call_001",
                "type": "function",
                "function": {
                    "name": "add",
                    "arguments": '{"a": 10, "b": 20}',
                },
            }
        ]
    }

    # 4. 执行工具调用
    results = await universe.dispatch(llm_response)

    # 5. 输出结果
    for result in results:
        print(f"\nResult: {result.result}")  # 输出: 30
        print(f"Success: {result.is_success}")


if __name__ == "__main__":
    asyncio.run(main())
