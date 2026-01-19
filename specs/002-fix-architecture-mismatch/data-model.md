# 数据模型: 架构一致性对齐

**分支**: `002-fix-architecture-mismatch`

## 核心实体

### 1. ToolSet (工具集合)
`Universe.__getitem__` 返回的集合对象，用于筛选后的渲染与查询。

| 字段 | 类型 | 描述 |
|------|------|------|
| `tools` | `List[ToolMetadata]` | 匹配过滤表达式的工具元数据列表 |
| `expression` | `Optional[ToolExpression]` | 当前筛选表达式（来自 `Tag/Prefix/And/Or/Not`） |
| `drivers` | `Dict[str, BaseDriver]` | 可用协议驱动池（用于渲染协商） |

### 2. ToolExpression (调度过滤规则)
`dispatch` 的安全过滤规则。

| 形式 | 类型 | 描述 |
|------|------|------|
| 表达式 | `ToolExpression` | 统一过滤入口（如 `Tag/Prefix/And/Or/Not` 或 `ToolName`） |
| 空 | `None` | 不进行过滤 |

### 3. ModelProfile (模型画像)
用于 `ToolSet.render` 协商驱动。

| 字段 | 类型 | 描述 |
|------|------|------|
| `name` | `str` | 模型名称（如 `gpt-4o`） |
| `capabilities` | `Set[str]` | 能力标识集合（如 `FC_NATIVE`） |
| `protocol_hint` | `Optional[str]` | 优先协议提示（可选） |

### 4. ToolCall (工具调用)
协议解析后得到的标准化调用。

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | `str` | 调用 ID |
| `name` | `str` | 工具名称 |
| `arguments` | `Dict[str, Any]` | 原始参数 |
| `context` | `Dict[str, Any]` | 运行时上下文（用于注入与中间件） |

### 5. ToolResult (工具结果)
每个工具调用的执行结果或错误。

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | `str` | 对应 ToolCall ID |
| `result` | `Any` | 成功结果 |
| `error` | `Optional[str]` | 错误信息（拒绝或执行失败） |
| `meta` | `Dict[str, Any]` | 诊断信息（如耗时、驱动名） |

### 6. MiddlewareObj (中间件封装)
用于中间件链组装与去重。

| 字段 | 类型 | 描述 |
|------|------|------|
| `func` | `Callable` | 中间件函数或实例 |
| `critical` | `bool` | 是否关键中间件 |
| `scope` | `Optional[ToolExpression]` | 作用域表达式 |
| `uid` | `str` | 稳定标识（类名/函数名或显式 uid） |

## 关系与约束

- `ToolSet.tools` 来自 `Universe` 注册表，必须保持与 `ToolExpression` 的匹配一致性。
- `ToolExpression` 对 `ToolCall.name` 进行过滤，不匹配时返回错误 `ToolResult` 且不执行；工具名过滤通过 `ToolName(ToolExpression)` 表达。
- `ModelProfile` 仅用于驱动协商，不参与执行流水线。
- `MiddlewareObj.uid` 必须稳定，缺省情况下由类名/函数名生成。

## 状态转换

`ToolCall` 生命周期：
`Parsed` -> `Filtered/Denied` -> `Context Injected` -> `Middleware Chain` -> `Executed` -> `ToolResult`  
并行执行时，`ToolResult` 输出顺序与 `ToolCall` 输入顺序一致。
