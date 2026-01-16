# 研究: 架构一致性对齐

**分支**: `002-fix-architecture-mismatch`
**状态**: 完成

## 决策记录

### 1. `ToolSet` 与 `__getitem__` 的语义对齐
**Decision**: `Universe.__getitem__` 对 `str` 统一视为标签筛选并返回 `ToolSet`，保留显式的工具名访问入口（如 `get(name)`）。
**Rationale**:
- 架构文档明确将 `str` 解释为 Tag 过滤，返回 `ToolSet`。
- 保留显式名称访问可避免破坏工具检索的可用性。
**Alternatives considered**:
- 维持 `str` 表示工具名、仅对 `ToolExpression` 返回集合视图（与文档不一致）。

### 2. `ToolSet.render` 的协议协商策略
**Decision**: `ToolSet.render(model_name)` 生成 `ModelProfile` 并以 `BaseDriver.can_handle(profile)` 打分择优；若传入驱动名则显式使用该驱动并跳过协商。
**Rationale**:
- 满足“显式协议优先 + 自动协商”的双通道需求。
- Driver 层封装协议差异，符合协议无关性原则。
**Alternatives considered**:
- 基于静态映射表选择驱动（维护成本高且难以扩展）。

### 3. 响应协议自动识别
**Decision**: Driver 增加 `can_handle_response(response)` 评分接口，`dispatch` 选择分数最高的驱动解析响应，未命中则返回明确错误但不中断调度。
**Rationale**:
- 将协议识别能力下沉到 Driver 层，保持核心逻辑纯净。
- 与架构中“Fingerprinting”阶段一致。
**Alternatives considered**:
- 由 `Universe` 直接解析协议（破坏协议无关性）。

### 4. `tool_filter` 安全过滤形式
**Decision**: `tool_filter` 仅支持 `ToolExpression`；工具名过滤通过实现 `ToolName(ToolExpression)` 统一过滤方式。不允许的调用返回带错误的 `ToolResult`，且不执行工具函数。
**Rationale**:
- 统一过滤入口，避免多种规则分支。
- 满足“返回明确错误但不中断调度”的要求。
**Alternatives considered**:
- 同时支持表达式与名称集合（规则分散，易产生分支行为差异）。

### 5. 中间件去重稳定标识
**Decision**: 当 `uid` 未显式提供时，默认使用中间件类名/函数 `__qualname__` 作为稳定标识，避免 `id()` 带来的不稳定性。
**Rationale**:
- 支持同类型中间件覆盖与更新。
- 避免对象 id 导致的去重失效。
**Alternatives considered**:
- 继续使用 `id()` 拼接（无法稳定去重）。

### 6. 多工具调用并行执行
**Decision**: 使用 `asyncio.gather` 并行执行 `execute_single_tool`，保持结果顺序与调用顺序一致，并对每个 `ToolCall.context` 进行独立拷贝以避免交叉污染。
**Rationale**:
- 满足性能目标与顺序稳定性要求。
- 独立上下文降低并发副作用风险。
**Alternatives considered**:
- 保持顺序执行（不满足性能目标）。

### 7. `bind` 扩展配置
**Decision**: `bind` 增加 `exclude`（方法名列表）与 `middlewares`（中间件配置）参数，注册时透传至 `ToolMetadata`。
**Rationale**:
- 满足批量绑定的排除与中间件配置需求。
- 统一注册入口，降低重复手工配置成本。
**Alternatives considered**:
- 仅通过逐个 `tool()` 注册（使用成本高）。

## 依赖项检查

- 不新增第三方依赖，沿用 `pydantic` 与标准库 `asyncio`。

## 风险评估

- **协议识别误判**: 响应格式相近可能导致驱动识别偏差。
  - *Mitigation*: 以评分方式择优并要求驱动实现显式指纹判断。
- **并行执行的副作用**: 共享上下文导致数据污染。
  - *Mitigation*: 每个调用使用独立 `context` 拷贝并保持纯函数工具优先。
- **驱动兼容性**: 新增协议驱动可能与现有工具定义不一致。
  - *Mitigation*: 契约测试覆盖 `render/parse` 的输入输出一致性。
