"""
UniTools SDK - 多协议支持示例

展示如何处理不同 LLM 提供商的响应格式：
- OpenAI: tool_calls 格式
- Anthropic: content[type=tool_use] 格式
- XML: <tool_call> 标签格式
- Markdown: ```tool_call 代码块格式

支持自动检测和显式指定驱动。
"""

import asyncio
import json

from uni_tool import (
    universe,
)


# =============================================================================
# 1. 注册测试工具
# =============================================================================


@universe.tool()
def greet(name: str, language: str = "en") -> str:
    """Greet a person in specified language.

    Args:
        name: Person's name.
        language: Language code (en, zh, ja).
    """
    greetings = {
        "en": f"Hello, {name}!",
        "zh": f"你好，{name}！",
        "ja": f"こんにちは、{name}！",
    }
    return greetings.get(language, f"Hi, {name}!")


@universe.tool()
def calculate(operation: str, a: float, b: float) -> float:
    """Perform a calculation.

    Args:
        operation: Operation type (add, sub, mul, div).
        a: First operand.
        b: Second operand.
    """
    ops = {
        "add": lambda x, y: x + y,
        "sub": lambda x, y: x - y,
        "mul": lambda x, y: x * y,
        "div": lambda x, y: x / y if y != 0 else float("inf"),
    }
    return ops.get(operation, lambda x, y: 0)(a, b)


# =============================================================================
# 2. 主程序 - 演示各种协议
# =============================================================================


async def main():
    print("=" * 60)
    print("UniTools SDK - Multi-Protocol Demo")
    print("=" * 60)

    # =========================================================================
    # 协议 1: OpenAI 格式
    # =========================================================================
    print("\n[Protocol 1] OpenAI Format")
    print("-" * 40)

    openai_response = {
        "tool_calls": [
            {
                "id": "call_openai_1",
                "type": "function",
                "function": {
                    "name": "greet",
                    "arguments": json.dumps({"name": "Alice", "language": "en"}),
                },
            },
            {
                "id": "call_openai_2",
                "type": "function",
                "function": {
                    "name": "calculate",
                    "arguments": json.dumps({"operation": "mul", "a": 7, "b": 6}),
                },
            },
        ]
    }

    # 方式 1: 自动检测协议
    print("  Auto-detected:")
    results = await universe.dispatch(openai_response)
    for r in results:
        print(f"    {r.id}: {r.result}")

    # 方式 2: 显式指定驱动
    print("  Explicit driver:")
    results = await universe.dispatch(openai_response, driver_or_model="openai")
    for r in results:
        print(f"    {r.id}: {r.result}")

    # =========================================================================
    # 协议 2: Anthropic 格式
    # =========================================================================
    print("\n[Protocol 2] Anthropic Format")
    print("-" * 40)

    anthropic_response = {
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_anthropic_1",
                "name": "greet",
                "input": {"name": "Bob", "language": "zh"},
            },
            {
                "type": "tool_use",
                "id": "toolu_anthropic_2",
                "name": "calculate",
                "input": {"operation": "add", "a": 100, "b": 200},
            },
        ]
    }

    print("  Auto-detected:")
    results = await universe.dispatch(anthropic_response)
    for r in results:
        print(f"    {r.id}: {r.result}")

    # =========================================================================
    # 协议 3: XML 格式 (适用于不支持原生 function calling 的模型)
    # =========================================================================
    print("\n[Protocol 3] XML Format")
    print("-" * 40)

    xml_response = """
    <tool_call>
        <name>greet</name>
        <arguments>{"name": "Charlie", "language": "ja"}</arguments>
    </tool_call>
    <tool_call>
        <name>calculate</name>
        <arguments>{"operation": "div", "a": 100, "b": 4}</arguments>
    </tool_call>
    """

    print("  Auto-detected:")
    results = await universe.dispatch(xml_response)
    for r in results:
        print(f"    {r.id}: {r.result}")

    # =========================================================================
    # 协议 4: Markdown 格式 (适用于纯文本场景)
    # =========================================================================
    print("\n[Protocol 4] Markdown Format")
    print("-" * 40)

    markdown_response = """
    Let me help you with that.

    ```tool_call
    {"name": "greet", "arguments": {"name": "David", "language": "en"}}
    ```

    And here's the calculation:

    ```tool_call
    {"name": "calculate", "arguments": {"operation": "sub", "a": 50, "b": 8}}
    ```
    """

    print("  Auto-detected:")
    results = await universe.dispatch(markdown_response)
    for r in results:
        print(f"    {r.id}: {r.result}")

    # =========================================================================
    # 渲染不同格式的 Schema
    # =========================================================================
    print("\n" + "=" * 60)
    print("Schema Rendering for Different Providers")
    print("=" * 60)

    # OpenAI Schema
    print("\n[OpenAI Schema]")
    openai_schema = universe.render("openai")
    print(f"  Format: list of {len(openai_schema)} tool definitions")
    print(f"  Sample: {openai_schema[0]['function']['name']}")

    # Anthropic Schema
    print("\n[Anthropic Schema]")
    anthropic_schema = universe.render("anthropic")
    print(f"  Format: list of {len(anthropic_schema)} tool definitions")
    print(f"  Sample: {anthropic_schema[0]['name']}")

    # XML Schema (for prompting)
    print("\n[XML Schema]")
    xml_schema = universe.render("xml")
    print("  Format: XML string for system prompt")
    print(f"  Preview: {xml_schema[:100]}...")

    # Markdown Schema (for prompting)
    print("\n[Markdown Schema]")
    md_schema = universe.render("markdown")
    print("  Format: Markdown string for system prompt")
    print(f"  Preview: {md_schema[:100]}...")

    # =========================================================================
    # 使用模型名自动选择驱动
    # =========================================================================
    print("\n" + "=" * 60)
    print("Model Name to Driver Mapping")
    print("=" * 60)

    model_mappings = [
        "gpt-4o",
        "gpt-3.5-turbo",
        "claude-3-sonnet",
        "claude-3.5-sonnet",
    ]

    for model in model_mappings:
        schema = universe.render(model)
        driver_type = "OpenAI" if isinstance(schema, list) and "function" in schema[0] else "Anthropic"
        print(f"  {model}: -> {driver_type} format")


if __name__ == "__main__":
    asyncio.run(main())
