# UniTools SDK

一个与协议无关的 LLM 工具调用 SDK，旨在提供统一的工具定义、执行和治理能力。

## 核心特性

*   **协议无关 (Protocol Agnosticism)**: 核心逻辑与特定 LLM 提供商解耦，通过 Driver 层适配 OpenAI, Anthropic 等不同协议。
*   **纵深防御 (Defense in Depth)**: 执行流经过 Query (过滤), Filter (权限), Middleware (运行时隔离) 多层防护。
*   **上下文隔离 (Context Isolation)**: 敏感上下文 (User ID, Token) 通过 `Injected` 模式注入，严禁作为参数直接传给 LLM。
*   **工具表达式 (Tool Expression)**: 强大的工具过滤和组合能力 (Tag, Prefix, Logic Operators)。
*   **中间件治理 (Middleware Governance)**: 内置审计 (Audit) 和监控 (Monitor) 中间件，支持自定义扩展。

## 快速开始

### 1. 安装

本项目使用 [uv](https://github.com/astral-sh/uv) 进行极速包管理。

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

初始化开发环境：

```bash
# 创建虚拟环境并安装依赖
uv sync

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### 2. 最小示例

```python
import asyncio
from uni_tool import universe

# 1. 注册工具
@universe.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

async def main():
    # 2. 生成 Schema (适配 OpenAI 格式)
    print("OpenAI Schema:", universe.render("openai"))

    # 3. 模拟 LLM 响应并执行
    llm_response = {
        "tool_calls": [{
            "id": "call_1",
            "type": "function",
            "function": {"name": "add", "arguments": '{"a": 1, "b": 2}'}
        }]
    }
    results = await universe.dispatch(llm_response)
    print(f"Result: {results[0].result}")  # Output: 3

if __name__ == "__main__":
    asyncio.run(main())
```

## 进阶使用

### 上下文注入 (Context Injection)

避免将敏感信息（如 UserID, Token）暴露给 LLM，而是通过上下文自动注入。

```python
from typing import Annotated
from uni_tool import universe, Injected

@universe.tool()
def transfer(
    amount: float,
    user_id: Annotated[str, Injected("uid")]  # 自动从 context 获取 "uid"
):
    return f"Transferred {amount} for {user_id}"

# 执行时传入 context
# await universe.dispatch(response, context={"uid": "user_123"})
```

### 中间件 (Middleware)

支持全局或特定作用域的中间件，用于日志、监控、权限控制等。

```python
from uni_tool import universe, AuditMiddleware, MonitorMiddleware

# 启用审计和监控
universe.use(AuditMiddleware())
universe.use(MonitorMiddleware())
```

### 工具表达式 (Tool Expressions)

使用强大的表达式语言筛选工具集。

```python
from uni_tool import universe, Tag, Prefix

# 仅选择 "finance" 标签且名称以 "api_" 开头的工具
finance_tools = universe[Tag("finance") & Prefix("api_")].tools

# 仅允许读取类工具执行
# await universe.dispatch(response, tool_filter=Tag("read"))
```

## 开发指南

详细开发准则请参考 `CLAUDE.md` 和 `.specify/memory/constitution.md`。

### 核心工作流

1.  **工具表达式开发 (Tool Expression)**:
    *   专注于 `uni_tool/core/expressions.py` 和相关逻辑。
    *   使用 `uv run pytest tests/unit/test_expression.py` 验证更改。

2.  **中间件开发 (Middleware)**:
    *   在 `uni_tool/middlewares/` 中实现新的中间件。
    *   确保遵循**纵深防御**和**上下文隔离**原则。
    *   使用 `uv run pytest tests/unit/test_middleware.py` 验证更改。

3.  **规范驱动开发**:
    *   使用 `/speckit` 系列命令进行功能开发。
