# 数据模型: UniTools SDK

**分支**: `001-unitools-sdk`

## 核心实体

### 1. ToolMetadata (工具元数据)
描述注册到 Universe 中的工具的静态属性。

| 字段 | 类型 | 描述 |
|------|------|------|
| `name` | `str` | 工具唯一名称 (Regex: `^[a-zA-Z0-9_-]+$`) |
| `description` | `str` | 工具描述 (来自 docstring) |
| `func` | `Callable` | 原始函数引用 |
| `is_async` | `bool` | 是否为异步函数 |
| `parameters_model` | `Type[BaseModel]` | Pydantic 动态生成的参数模型 (仅包含 LLM 可见参数) |
| `injected_params` | `Dict[str, str]` | 注入参数映射 `{arg_name: context_key}` |
| `tags` | `Set[str]` | 标签集合 |
| `middlewares` | `List[MiddlewareObj]` | 工具级中间件列表 |

### 2. ToolCall (工具调用请求)
表示 LLM 发起的一次调用请求，贯穿中间件流水线。

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | `str` | 调用 ID (如 OpenAI call_id) |
| `name` | `str` | 调用的工具名称 |
| `arguments` | `Dict[str, Any]` | LLM 提供的原始参数 |
| `context` | `Dict[str, Any]` | 上下文数据 (用于依赖注入和中间件通信) |

### 3. ToolResult (执行结果)
工具执行后的返回结果。

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | `str` | 对应的 ToolCall ID |
| `result` | `Any` | 函数返回值 (如果成功) |
| `error` | `Optional[str]` | 错误信息 (如果失败) |
| `meta` | `Dict[str, Any]` | 额外元数据 (如执行耗时) |

### 4. MiddlewareObj (中间件封装)
封装中间件函数及其配置。

| 字段 | 类型 | 描述 |
|------|------|------|
| `func` | `Callable` | 中间件函数 `async (call, next) -> result` |
| `critical` | `bool` | 是否为关键中间件 (失败是否阻断) |
| `scope` | `ToolExpression` | 作用域表达式 |
| `uid` | `str` | 唯一标识 (用于去重) |

## 辅助实体

### 5. ToolExpression (筛选表达式)
用于逻辑筛选工具。

- **子类**: `Tag(name)`, `Prefix(prefix)`
- **操作**: `And(&)`, `Or(|)`, `Not(~)`

### 6. Driver (驱动接口)
协议适配器。

- **Render Input**: `List[ToolMetadata]`
- **Render Output**: `Any` (e.g., JSON Schema Dict)
- **Parse Input**: `Any` (LLM Response)
- **Parse Output**: `List[ToolCall]`

## 状态转换

- **ToolCall 生命周期**:
  `Created (Driver.parse)` -> `Context Enriched (Universe.dispatch)` -> `Middleware Processing` -> `Executed (ToolMetadata.func)` -> `Result Encapsulated (ToolResult)`
