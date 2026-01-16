# UniTools SDK Examples

本目录包含 UniTools SDK 的各种使用示例，从基础到高级逐步展示核心功能。

## 运行示例

```bash
# 确保在项目根目录
cd /path/to/uni-tool

# 激活虚拟环境
source .venv/bin/activate

# 运行任意示例
uv run python examples/01_minimal.py
```

## 示例列表

### 01_minimal.py - 最小示例

**适合人群**：首次接触 UniTools SDK 的用户

**展示内容**：
- 使用 `@universe.tool()` 注册工具
- 使用 `universe.render()` 生成 LLM 所需的 schema
- 使用 `universe.dispatch()` 执行工具调用

```python
@universe.tool()
def add(a: int, b: int) -> int:
    return a + b

results = await universe.dispatch(llm_response)
```

---

### 02_all_in_one.py - 完整功能示例

**适合人群**：想要快速了解全部功能的用户

**展示内容**：
- 同步/异步工具注册
- 上下文注入 (`Injected`)
- 标签过滤 (`Tag`)
- 中间件 (`Audit`/`Monitor`)
- 类绑定 (`@bind`)
- 工具过滤器 (`tool_filter`)

---

### 03_middleware.py - 中间件示例

**适合人群**：需要实现审计、监控、权限控制的用户

**展示内容**：
- 内置中间件：`AuditMiddleware`, `MonitorMiddleware`
- 自定义中间件：权限检查、速率限制
- 作用域中间件：仅对特定标签的工具生效

```python
# 自定义权限中间件
async def permission_middleware(call, next_handler):
    if call.name in admin_tools and user_role != "admin":
        raise PermissionError("需要管理员权限")
    return await next_handler(call)

universe.use(permission_middleware, critical=True)
```

---

### 04_class_binding.py - 类绑定示例

**适合人群**：需要批量注册服务类方法的用户

**展示内容**：
- 使用 `@universe.bind()` 批量注册类方法
- 添加前缀避免命名冲突
- 排除特定方法
- 在类方法中使用上下文注入

```python
@universe.bind(prefix="math_", tags={"math"})
class MathService:
    def add(self, a: float, b: float) -> float:
        return a + b
# 注册为 "math_add"
```

---

### 05_tool_filtering.py - 工具过滤示例

**适合人群**：需要细粒度控制工具访问的用户

**展示内容**：
- `Tag`: 按标签过滤
- `Prefix`: 按名称前缀过滤
- `ToolName`: 精确名称匹配
- `And`, `Or`, `Not`: 组合表达式
- `tool_filter`: 在 dispatch 时限制可执行的工具

```python
# 复杂过滤表达式
universe[Tag("api") & Tag("read") & ~Tag("internal")]

# 在 dispatch 时限制
await universe.dispatch(response, tool_filter=Tag("public"))
```

---

### 06_multi_protocol.py - 多协议示例

**适合人群**：需要支持多种 LLM 提供商的用户

**展示内容**：
- OpenAI 格式：`tool_calls`
- Anthropic 格式：`content[type=tool_use]`
- XML 格式：`<tool_call>` 标签
- Markdown 格式：\`\`\`tool_call 代码块
- 自动协议检测
- 为不同提供商渲染 schema

```python
# 自动检测协议
results = await universe.dispatch(any_format_response)

# 渲染特定格式
openai_schema = universe.render("openai")
anthropic_schema = universe.render("anthropic")
```

---

### 07_real_world_chatbot.py - 真实世界场景

**适合人群**：准备投入生产使用的用户

**展示内容**：
- 完整的业务域设计（订单、产品、用户）
- 中间件链配置
- 基于角色的权限控制
- 错误处理和结果格式化
- 模拟真实的客服机器人场景

```python
class ChatBot:
    def __init__(self, user_id: str, role: str):
        self.context = {"current_user_id": user_id}
        self.tool_filter = None if role == "admin" else ~Tag("admin")

    async def handle(self, llm_response):
        return await universe.dispatch(
            llm_response,
            context=self.context,
            tool_filter=self.tool_filter,
        )
```

## 核心概念速查

| 概念 | 说明 | 示例 |
|------|------|------|
| `@universe.tool()` | 注册单个工具 | `@universe.tool(tags={"api"})` |
| `@universe.bind()` | 批量注册类方法 | `@universe.bind(prefix="svc_")` |
| `Injected` | 上下文注入 | `user_id: Annotated[str, Injected("uid")]` |
| `Tag` | 标签过滤 | `universe[Tag("finance")]` |
| `universe.render()` | 生成 schema | `schema = universe.render("openai")` |
| `universe.dispatch()` | 执行工具调用 | `results = await universe.dispatch(response)` |
| `universe.use()` | 注册中间件 | `universe.use(audit, critical=False)` |
| `tool_filter` | 运行时过滤 | `dispatch(..., tool_filter=~Tag("admin"))` |
