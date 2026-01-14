"""
类绑定示例 (Class Binding)

展示如何使用 @universe.bind 将一个类实例的所有公共方法注册为工具。
这对于将现有的服务类快速转换为工具集非常有用。
"""

import asyncio
from uni_tool import Universe
from uni_tool.core.models import ToolCall
from uni_tool.core.execution import execute_tool_calls

universe = Universe()


# 1. 定义并绑定类
# 使用 @universe.bind 装饰器，自动扫描并注册所有 public 方法
# prefix 参数会自动给所有工具名加上前缀
@universe.bind(prefix="math_")
class MathService:
    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b

    def divide(self, a: int, b: int) -> float:
        """Divide two numbers."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

    def _helper(self):
        """Internal method, will NOT be registered."""
        pass


async def main():
    print("=== 02 Class Binding ===")

    # 验证工具是否已注册
    tool = universe.get("math_multiply")
    if tool:
        print(f"Tool found: {tool.name} - {tool.description}")

    # 2. 执行类方法工具
    calls = [
        ToolCall(id="call_1", name="math_multiply", arguments={"a": 4, "b": 5}),
        ToolCall(id="call_2", name="math_divide", arguments={"a": 10, "b": 2}),
    ]

    print("Executing batch calls...")
    results = await execute_tool_calls(universe, calls)

    for res in results:
        print(f"Result ({res.id}): {res.result}")


if __name__ == "__main__":
    asyncio.run(main())
