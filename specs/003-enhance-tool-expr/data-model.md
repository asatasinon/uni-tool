# 数据模型: ToolExpression 增强

**分支**: `003-enhance-tool-expr`

## 核心实体

### 1. ToolExpression (增强)
工具过滤表达式基类，新增字符串化、诊断与简化能力。

| 字段/方法 | 类型 | 描述 |
|---|---|---|
| `matches(metadata)` | `bool` | 判断工具是否命中 |
| `diagnose(metadata)` | `ExpressionTrace` | 返回诊断路径与失败原因 |
| `simplify()` | `ToolExpression` | 返回简化后的表达式 |
| `to_dsl()` | `str` | 生成可被解析器还原的 DSL 字符串 |

**主要子类**:
- `And(left, right)`
- `Or(left, right)`
- `Not(expr)`
- `Tag(name)`
- `Prefix(prefix)`
- `ToolName(name)`

### 2. ExpressionParser
负责 DSL 字符串到 `ToolExpression` 的解析。

| 字段/方法 | 类型 | 描述 |
|---|---|---|
| `parse(text)` | `ToolExpression` | 解析 DSL 字符串 |

**语法简写**:
- `^tool_` 等价于 `prefix:tool_`
- `` `tool_name` `` 等价于 `name:tool_name`

### 3. ExpressionTrace
表达式诊断结果节点。

| 字段 | 类型 | 描述 |
|---|---|---|
| `matched` | `bool` | 当前节点是否命中 |
| `node` | `str` | 节点类型（如 `Tag`, `And`） |
| `detail` | `str` | 命中/失败原因 |
| `children` | `List[ExpressionTrace]` | 子节点诊断 |

### 4. ExpressionParseError
DSL 解析错误模型。

| 字段 | 类型 | 描述 |
|---|---|---|
| `message` | `str` | 语法错误信息 |
| `line` | `int` | 错误行号 |
| `column` | `int` | 错误列号 |
| `context` | `str` | 错误上下文片段 |

## 关系说明

- `ExpressionParser.parse` 输出 `ToolExpression` 树。
- `ToolExpression.diagnose` 生成 `ExpressionTrace` 树。
- `ToolExpression.simplify` 输出新的表达式树，保持语义等价。
