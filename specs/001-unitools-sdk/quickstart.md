# UniTools SDK 快速入门

## 安装

```bash
uv add unitools-sdk
```

## 核心概念

- **Universe**: 全局单例，管理所有工具。
- **@u.tool**: 注册函数为工具。
- **Injected**: 声明运行时依赖注入参数。
- **Driver**: 适配不同的 LLM。

## 基本用法

```python
import asyncio
from typing import Annotated
from unitools import universe, Injected, Tag

# 1. 直接使用全局单例对象 `universe`
# universe = Universe() # 不再需要手动实例化

# 2. 注册工具 (含依赖注入)
@universe.tool(tags=["finance"])
async def get_balance(
    currency: str, 
    user_id: Annotated[str, Injected("uid")] # 自动从 context['uid'] 注入
):
    """查询用户余额"""
    print(f"Checking balance for user {user_id} in {currency}")
    return {"amount": 100.0, "currency": currency}

# 3. 注册中间件
async def audit_middleware(call, next_handler):
    print(f"[Audit] invoking {call.name}")
    try:
        result = await next_handler(call)
        print(f"[Audit] success: {result}")
        return result
    except Exception as e:
        print(f"[Audit] failed: {e}")
        raise

universe.use(audit_middleware)

async def main():
    # 4. 导出给 LLM (OpenAI 格式)
    tools_schema = universe[Tag("finance")].render("gpt-4o")
    # print(json.dumps(tools_schema, indent=2))
    
    # 5. 模拟执行 (Dispatch)
    # 假设 LLM 返回了如下 Tool Call
    mock_llm_response = {
        "tool_calls": [{
            "id": "call_123",
            "function": {
                "name": "get_balance",
                "arguments": '{"currency": "USD"}'
            },
            "type": "function"
        }]
    }
    
    # 执行，并注入 context
    results = await universe.dispatch(
        mock_llm_response, 
        context={"uid": "user_001"}
    )
    print(results)

if __name__ == "__main__":
    asyncio.run(main())
```

## 常见错误处理

- `DuplicateToolError`: 注册重名工具时抛出。
- `MissingContextKeyError`: 缺少必要的注入参数时抛出。
