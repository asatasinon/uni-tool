# 研究: UniTools SDK 实现细节

**分支**: `001-unitools-sdk`
**状态**: 完成

## 决策记录

### 1. 文档字符串解析库选择
**Decision**: 使用 `docstring_parser` 库。
**Rationale**: 
- 该库轻量且无繁重依赖。
- 支持 Google, NumPy, Sphinx 等多种主流文档风格，无需额外配置即可自动探测。
- 对于 SDK 而言，兼容用户不同的文档习惯至关重要。
**Alternatives considered**: 
- `griffe`: 功能更强大但过于沉重，主要用于静态分析工具。
- `sphinx`: 依赖过重，不适合作为运行时依赖。

### 2. 动态模型生成 (Pydantic V2)
**Decision**: 使用 `pydantic.create_model` 结合 `inspect.signature`。
**Rationale**:
- Pydantic V2 提供了完善的动态模型创建 API。
- 需要在遍历函数参数时，识别 `Annotated[T, Injected(...)]`，将其从生成的 Pydantic 模型字段中排除，但保留在 `ToolMetadata.injected_params` 映射中。
- 这样生成的 JSON Schema 将自动不包含注入参数，符合 "LLM 不可见" 的原则。

### 3. 同步/异步混合执行策略
**Decision**: 统一在 `async def` 包装器中处理，同步函数使用 `asyncio.to_thread` 运行。
**Rationale**:
- `Universe.dispatch` 是异步入口，必须非阻塞。
- 用户注册的工具可能是同步的（如计算密集型或旧代码）。
- `asyncio.to_thread` (Python 3.9+) 是在独立线程运行同步代码的标准方式，避免阻塞事件循环。

### 4. 中间件异常隔离机制
**Decision**: 在 `_wrap_middleware` 闭包中显式捕获 `Exception`。
**Rationale**:
- 区分 `critical` 属性。
- 如果 `critical=True`，捕获异常后直接 `raise`。
- 如果 `critical=False`，捕获异常后记录日志 (Logger)，然后调用 `next_handler(call)` 跳过该中间件，确保流水线不中断。

### 5. 内置治理能力实现
**Decision**: 将审计 (Audit)、监控 (Monitor)、告警 (Alert) 实现为标准中间件类。
**Rationale**:
- 符合 "Based Middleware Governance" 原则。
- `AuditMiddleware`: 记录输入输出和耗时。
- `MonitorMiddleware`: 收集 Metrics (如 Prometheus 格式，可选支持)。
- `AlertMiddleware`: 捕获 `ToolExecutionError` 并触发回调。
- 这样用户可以灵活选择开启或替换实现。

### 6. 上下文传递 (Context Propagation)
**Decision**: 使用显式的参数传递 (`ToolCall.context`) 而非 `contextvars`。
**Rationale**:
- `ToolCall` 对象贯穿整个中间件链。
- 显式传递更易于调试和测试，减少 "隐式全局变量" 的心智负担。
- `contextvars` 更适合跨越库边界的深层调用，而在洋葱模型中，每一层都显式接收 `call` 对象。

### 7. 全局单例模式 (Singleton Pattern)
**Decision**: 在 `__init__.py` 中直接导出预实例化的 `universe` 对象。
**Rationale**:
- 简化用户调用，`from unitools import universe` 即可使用，无需 `u = Universe()`。
- 符合 Python 社区习惯 (如 `flask.current_app`, `requests.api` 等模块级接口)。
- 底层 `Universe` 类仍保持单例实现，以防止用户通过类实例化时创建多份副本。

## 依赖项检查

- `pydantic`: 核心依赖，已确认 V2 API 适用。
- `docstring_parser`: 需添加到 `pyproject.toml`。
- `pytest-asyncio`: 需添加到开发依赖。

## 风险评估

- **Pydantic V2 兼容性**: 用户如果传入了旧版 Pydantic V1 的类型对象可能会有兼容问题。
  - *Mitigation*: 明确声明 SDK 依赖 Pydantic V2，并在运行时检查版本。
- **性能开销**: 过深的中间件链可能带来微小的延迟。
  - *Mitigation*: 核心路径保持纯 Python 调用，避免不必要的序列化/反序列化。
- **单例状态污染**: 在测试场景下，单例可能导致测试用例间的状态污染。
  - *Mitigation*: 提供 `Universe._reset()` 或类似方法仅供测试使用，以便清理全局状态。
