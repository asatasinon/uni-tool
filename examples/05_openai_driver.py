"""
OpenAI 驱动示例 (OpenAI Driver)

展示如何使用 OpenAIDriver 生成 JSON Schema 供 LLM 使用，
并解析 LLM 的响应以执行工具。
"""

import asyncio
import json
from uni_tool import Universe
from uni_tool.drivers.openai import OpenAIDriver
from uni_tool.core.execution import execute_tool_calls

universe = Universe()
driver = OpenAIDriver()


@universe.tool(name="get_weather")
def get_weather(location: str, unit: str = "celsius") -> str:
    """
    Get the current weather in a given location.

    Args:
        location: The city and state, e.g. San Francisco, CA.
        unit: Temperature unit (celsius or fahrenheit).
    """
    return f"Weather in {location} is 22 degrees {unit}"


async def main():
    print("=== 05 OpenAI Driver ===")

    # 1. Render: 生成工具定义 (JSON Schema)
    # 这些定义将发送给 OpenAI API (tools=...)
    tools_schema = driver.render(list(universe.tools.values()))
    print("Generated Tools Schema:")
    print(json.dumps(tools_schema, indent=2))

    # 2. Mock LLM Response: 模拟 OpenAI 的响应
    # 在实际应用中，这里是 client.chat.completions.create(...) 的返回值
    mock_openai_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_abc123",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"location": "Beijing", "unit": "celsius"}',
                            },
                        }
                    ],
                }
            }
        ]
    }

    print("\nMock LLM Response Received.")

    # 3. Parse: 解析响应为 ToolCall 对象
    tool_calls = driver.parse(mock_openai_response)
    print(f"Parsed {len(tool_calls)} tool call(s).")

    # 4. Execute: 执行工具
    results = await execute_tool_calls(universe, tool_calls)

    for res in results:
        print(f"Result from {res.id}: {res.result}")


if __name__ == "__main__":
    asyncio.run(main())
