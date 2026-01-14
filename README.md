# UniTools SDK：全场景 LLM 插件集成框架

## 1. 设计愿景

`UniTools` 是一个为 AI Agent 开发者设计的全栈工具调用 SDK。它通过统一的声明式编程模型，解决了大模型插件开发中**协议碎片化**、**参数校验难**、**执行链路不可控**以及**文档维护滞后**等核心痛点。

### 核心价值
- **Write Once, Call Everywhere**：一套代码同时适配 OpenAI、Claude 及国产大模型。
- **强类型契约**：利用 Python 类型注解和 Pydantic 建立 LLM 与代码间的“硬边界”。
- **工业级可观测性**：通过中间件链（Middleware Chain）实现全链路日志、鉴权与性能监控。

---

## 2. 核心模块架构

### 2.1 注册中心 (Registry) — 元数据定义
注册中心负责将 Python 代码翻译为结构化的工具元数据对象 `ToolMetadata`。

#### A. `@tool` 装饰器：原子级提取
- **签名解析**：利用 `inspect.signature` 提取参数名、类型注解和默认值。
- **类型模型化**：使用 `pydantic.create_model` 将函数签名实时转换为 Pydantic 类。这使得 SDK 拥有了**运行时强制校验**和**类型强制转换**（如字符串转枚举）的能力。
- **描述增强**：
    - 优先读取 `Annotated[T, Field(description="...")]`。
    - 自动解析 Docstring（支持 Google/NumPy 风格），提取函数简介及每个参数的详细描述。
- **异步标记**：自动识别 `async def`，确保 Executor 能够正确调度。

#### B. `@bind` 类装饰器：模块化分组
- **批量扫描**：遍历类中所有非下划线开头的 Public 方法。
- **生命周期管理**：自动管理实例。当绑定一个类时，SDK 会保留一个实例；也支持直接绑定已初始化的对象。
- **标签/前缀扩散**：类级别的 `tags` 和 `prefix` 自动继承给内部所有工具，支持“一键场景化”。

#### C. `@ignore`：显式排除
- 用于在类绑定模式下，保护内部辅助方法不被暴露给 LLM。

### 2.2 适配器层 (Adapter) — 多协议方言
适配器负责将 `ToolMetadata` 转换为不同 LLM 能理解的“语言”。

- **OpenAIAdapter (JSON Schema)**：
    - 核心细节：执行 **Schema 清洗**，递归删除 OpenAI 不支持的 `title`、`definitions`、`additionalProperties` 等字段，防止 API 报错。
- **XmlPromptAdapter (无 FC 模型支持)**：
    - 将工具描述转换为结构化的 XML 块。
    - 提供配套的 `RegexParser`，专门从 LLM 的流式输出或全文中提取 `<call name="..">{..}</call>` 格式并还原为 JSON。
- **MarkdownAdapter (文档化)**：
    - 自动将 Schema 展平为易读的参数表格，支持生成调用示例。

### 2.3 中间件执行器 (Middleware Executor) — 洋葱模型
Executor 采用类似 Koa/FastAPI 的中间件机制，拦截每一次工具调用。

- **递归链构建**：每一个中间件都持有 `next_handler`。
- **核心中间件应用**：
    - **ValidationMiddleware**：在最内层进行 Pydantic 校验。若失败，不抛出系统异常，而是返回结构化的 `ToolResponse(is_error=True, content=...)`。
    - **ContextInjectionMiddleware**：识别被标记为 `Internal` 的参数，从 `context` 字典中注入真实值（如 `current_user_id`），实现 LLM 无法感知但代码能拿到的隐私参数。
    - **AuthMiddleware**：基于 `ToolMetadata` 的标签进行权限检查。

---

## 3. 核心功能实现细节

### 3.1 运行时自修复 (Self-Correction)
这是提高 Agent 鲁棒性的关键细节：
1. **捕获错误**：当 LLM 传参不符合 Pydantic 定义时（如缺少参数、格式错误），`ValidationMiddleware` 会捕获 `ValidationError`。
2. **错误美化**：将 Pydantic 晦涩的 JSON 错误转换为自然语言描述：“你提供的 `start_date` 格式不正确，请使用 YYYY-MM-DD 格式。”
3. **反馈闭环**：该错误作为工具结果返回给 LLM。由于 LLM 有“根据反馈修正”的能力，它会自动发起第二次正确的调用。

### 3.2 高并发并行处理 (Batch Execution)
对于模型一次性返回的多个工具调用：
- **混合调度**：
    - **Async 工具**：使用 `asyncio.gather` 并发执行。
    - **Sync 工具**：使用 `asyncio.to_thread` 分发到外部线程池，防止阻塞事件循环。
- **结果对齐**：即使工具并行完成的时间不一致，`BatchExecutor` 也会确保结果按照 LLM 请求的顺序（或对应的 ID）进行排列，以便正确回填对话历史。

### 3.3 动态过滤系统 (Tool Filter)
通过重载 Python 的运算符，实现极其灵活的工具加载策略：
- **TagFilter**：基于标签（如 `finance`, `ops`）。
- **PrefixFilter**：基于名字前缀。
- **逻辑组合**：支持 `filter = (TagFilter("A") | TagFilter("B")) & ~PrefixFilter("internal_")`。
- **用途**：在 Prompt 生成时过滤可见工具；在执行时进行动态越权检查。

---

## 4. 关键代码示例

### 4.1 注册工具类
```python
@registry.bind(prefix="DB__", tags=["data-access"])
class DatabaseTool:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    @registry.tool(tags=["readonly"])
    async def query_user(self, user_id: Annotated[int, Field(description="用户ID")]):
        """查询用户信息"""
        return f"User {user_id} info from {self.conn_str}"

    @ignore
    def _helper(self): pass
```

### 4.2 执行与中间件
```python
async def log_middleware(call, next_h):
    print(f"Calling {call.name}")
    return await next_h(call)

executor = ToolExecutor(registry)
executor.use(log_middleware)

# 执行调用
response = await executor.execute(
    name="DB__query_user", 
    arguments={"user_id": "123"}, # 字符串会自动转为 int
    context={"request_id": "req_001"}
)
```

---

## 5. 文档与工具维护
- **自动生成 MD**：`registry.export(MarkdownAdapter)` 可直接生成项目的 API 文档。
- **XML 注入**：对于 Llama 系列模型，直接将 `registry.export(XmlPromptAdapter)` 的输出拼接至 System Prompt 即可完成适配。

---

## 6. 总结

| 维度 | 实现细节 | 收益 |
| :--- | :--- | :--- |
| **注册层** | 动态 Pydantic 模型 + Docstring 解析 | 零成本同步代码与 Schema，减少幻觉 |
| **执行层** | 异步洋葱模型中间件 + 线程池分发 | 极高的扩展性，支持权限、日志与并发执行 |
| **适配层** | 递归 Schema 清洗 + XML 正则解析器 | 一套代码兼容所有主流模型及 Legacy 模型 |
| **安全层** | 运算符重载过滤器 + 运行时隔离 | 确保 LLM 只能调用当前场景被授权的工具 |
| **自愈层** | 结构化错误回传 LLM | 显著提升多步推理任务的成功率 |

该方案不仅是一个简单的 Wrapper，更是一个完整的 **LLM 工具治理体系**，适用于从简单的对话助手到复杂的自治 Agent 系统的所有场景。