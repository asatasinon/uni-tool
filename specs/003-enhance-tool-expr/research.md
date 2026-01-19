# 研究: ToolExpression DSL 与诊断实现

**分支**: `003-enhance-tool-expr`
**状态**: 完成

## 决策记录

### 1. 解析器实现方式
**Decision**: 使用 Lark 的 LALR 解析器，并通过分层规则表达操作符优先级。
**Rationale**:
- 规范要求使用 Lark。
- LALR 解析性能稳定，适合频繁解析与配置场景。
- Lark 文档示例表明可用 `?expr`/`?term` 分层规则表达 `|`、`&`、`~` 的优先级。
**Alternatives considered**:
- Earley 解析器（更通用但性能较低）。
- 手写递归下降解析器（违背规范约束）。

### 2. DSL 标识符约束
**Decision**: 标识符使用严格正则（如 `[A-Za-z0-9_-]+`），拒绝空格与 DSL 关键字符。
**Rationale**:
- 规范明确禁止空格与 DSL 关键字符。
- 在 Lexer 阶段拒绝非法输入，错误更直观。
- 与现有工具名/标签命名习惯一致。
**Alternatives considered**:
- 支持引号包裹标识符（不符合规范要求）。

### 3. 解析错误处理
**Decision**: 捕获 `lark.exceptions.UnexpectedInput`，转换为 SDK 的明确语法错误，并附带上下文、行列号。
**Rationale**:
- Lark 提供 `get_context`、`line`、`column`，可生成清晰错误。
- 满足规范要求的“明确解析错误”。
**Alternatives considered**:
- 直接透传 Lark 异常（用户不易理解）。

### 4. AST 构建方式
**Decision**: 使用类式 `Transformer` 将 parse tree 转换为 `ToolExpression` 节点。
**Rationale**:
- 逻辑清晰，便于单元测试与扩展。
- 避免在函数内嵌套函数，符合项目约束。
**Alternatives considered**:
- 手动遍历 parse tree（实现繁琐）。

### 5. 简化规则集合
**Decision**: 采用规则化简：扁平化、去重、双重否定消除。
**Rationale**:
- 对应规范的性能优化诉求。
- 规则简单、可预测，避免引入复杂依赖。
**Alternatives considered**:
- 引入布尔代数求简库（过重且维护成本高）。

### 6. 字符串化策略
**Decision**: 在表达式节点实现 `to_dsl()`，按操作符优先级添加必要括号。
**Rationale**:
- 确保序列化结果可被解析器稳定还原。
- 便于诊断输出与调试。
**Alternatives considered**:
- 基于 `__repr__` 输出（不保证 DSL 兼容）。

### 7. DSL 简写语法
**Decision**: 支持 `^tool_` 作为 `prefix:tool_` 的简写，支持 `` `tool_name` `` 作为 `name:tool_name` 的简写。
**Rationale**:
- 降低配置心智负担，便于阅读与迁移旧规则。
- 明确简写到核心语义的映射，便于解析器实现。
**Alternatives considered**:
- 仅保留 `prefix:`/`name:` 完整写法（可读性较弱）。

## 依赖项检查

- `lark`: 新增依赖，需通过 `uv add lark` 引入。

## 风险评估

- **语法歧义**: 优先级规则设计不当可能导致解析歧义。
  - *Mitigation*: 使用分层规则定义 `OR -> AND -> NOT -> ATOM`，并覆盖边界用例测试。
- **错误信息一致性**: 不同类型语法错误提示不一致。
  - *Mitigation*: 统一捕获并格式化为 SDK 的解析错误结构。
