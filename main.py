import asyncio
from uni_tool import universe, Injected, Tag
from typing import Annotated

async def main():
    @universe.tool(tags={"finance"})
    async def get_balance(
        currency: str,
        user_id: Annotated[str, Injected("uid")]  # 从 context 注入
    ):
        """获取用户余额"""
        return {"amount": 100.0, "currency": currency}

    # 渲染工具给 LLM
    schema = universe[Tag("finance")].render("gpt-4o")

    # 执行 LLM 返回的调用
    results = await universe.dispatch(
        {
            "tool_calls": [
                {
                    "id": "call_123",
                    "function": {
                        "name": "get_balance",
                        "arguments": '{"currency": "USD"}'
                    },
                }
            ]
        },
        context={"uid": "user_001"}
    )

    print(results)


if __name__ == "__main__":
    asyncio.run(main())
