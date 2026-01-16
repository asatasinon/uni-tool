# 架构一致性对齐 快速入门

## 前置条件

- 使用 `uv sync` 安装依赖后，执行 `source .venv/bin/activate` 激活虚拟环境。

## 1. 注册驱动与工具

```python
import asyncio
from typing import Annotated
from uni_tool import universe, Injected, Tag, ToolName
from uni_tool.drivers import OpenAIDriver, AnthropicDriver, XMLDriver, MarkdownDriver


def register_default_drivers() -> None:
    universe.register_driver('openai', OpenAIDriver())
    universe.register_driver('anthropic', AnthropicDriver())
    universe.register_driver('xml', XMLDriver())
    universe.register_driver('markdown', MarkdownDriver())


@universe.tool(tags={'finance'})
async def get_balance(
    currency: str,
    user_id: Annotated[str, Injected('uid')],
) -> dict:
    return {'amount': 100.0, 'currency': currency, 'user_id': user_id}


@universe.tool(tags={'finance', 'internal'})
async def rotate_finance_key() -> dict:
    return {'status': 'rotated'}


async def run_demo() -> None:
    register_default_drivers()

    tool_set = universe['finance']  # Tag 过滤 -> ToolSet
    tools_schema = tool_set.render('gpt-4o')  # 自动协商协议
    explicit_schema = tool_set.render('openai')  # 显式指定协议驱动

    response = {
        'tool_calls': [
            {
                'id': 'call_001',
                'type': 'function',
                'function': {'name': 'get_balance', 'arguments': '{"currency": "USD"}'},
            },
            {
                'id': 'call_002',
                'type': 'function',
                'function': {'name': 'rotate_finance_key', 'arguments': '{}'},
            },
        ],
    }

    results = await universe.dispatch(
        response,
        context={'uid': 'user_001'},
        tool_filter=Tag('finance') & ~Tag('internal'),
    )
    print(tools_schema, explicit_schema, results)


if __name__ == '__main__':
    asyncio.run(run_demo())
```

## 2. 使用 ToolName 进行工具名过滤

```python
results = await universe.dispatch(
    response,
    context={'uid': 'user_001'},
    tool_filter=ToolName('get_balance'),
)
```
