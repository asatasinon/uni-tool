# 与 `docs/architecture.md` 的不一致项与修复建议

本文档基于当前代码与架构文档对照，列出已验证的不一致项，并给出修复建议。

## 1. `__getitem__` 对 `str` 的语义与返回类型不一致

文档描述 `str` 表示 Tag 过滤并返回 ToolSet，但当前实现将 `str` 作为工具名查找并返回 ToolMetadata，同时对表达式返回 UniverseView。

证据：
```166:192:uni_tool/core/universe.py
    @overload
    def __getitem__(self, key: str) -> ToolMetadata: ...

    @overload
    def __getitem__(self, key: ToolExpression) -> UniverseView: ...

    def __getitem__(self, key: str | ToolExpression) -> ToolMetadata | UniverseView:
        """
        Access tools by name or filter by expression.
        """
        if isinstance(key, str):
            if key not in self._registry:
                raise ToolNotFoundError(key)
            return self._registry[key]
        elif isinstance(key, ToolExpression):
            return UniverseView(self, key)
```

修复建议：
- 将 `str` 解释为 Tag 过滤并返回 ToolSet（如需保留通过名称访问工具，增加显式方法，如 `get()`）。
- 新增 ToolSet 类型并替代 UniverseView 作为筛选结果的返回值。

## 2. ToolSet 组件缺失且 `render` 未进行协议协商

文档描述 `ToolSet.render(model_name)` 会根据模型画像协商驱动，但当前实现只有 UniverseView 且直接依赖驱动名称或别名。

证据：
```36:55:uni_tool/core/universe.py
class UniverseView:
    """
    A filtered view of the Universe for a specific tool expression.
    """

    def __init__(self, universe: "Universe", expression: ToolExpression):
        self._universe = universe
        self._expression = expression

    def get_tools(self) -> List[ToolMetadata]:
        """Get all tools matching the expression."""
        return [meta for meta in self._universe._registry.values() if self._expression.matches(meta)]

    def render(self, driver_or_model: str) -> Any:
        """Render the filtered tools using the specified driver."""
        driver = self._universe._get_driver(driver_or_model)
        return driver.render(self.get_tools())
```

修复建议：
- 增加 ToolSet 类型，提供 `render(model_name)` 与 `to_markdown()`。
- 引入模型画像与驱动打分选择逻辑，替换仅基于别名映射的驱动选择。

## 3. `dispatch` 缺少 `tool_filter` 安全过滤层

文档描述 `dispatch` 支持 `tool_filter` 并在执行前做权限过滤，但当前实现没有该参数与过滤逻辑。

证据：
```270:298:uni_tool/core/universe.py
    async def dispatch(
        self,
        response: Any,
        *,
        context: Optional[Dict[str, Any]] = None,
        driver_or_model: str = "openai",
    ) -> List[ToolResult]:
        """
        Parse and execute tool calls from an LLM response.
        """
        from uni_tool.core.execution import execute_tool_calls

        driver = self._get_driver(driver_or_model)
        calls = driver.parse(response)

        # Enrich calls with context
        if context:
            for call in calls:
                call.context.update(context)

        return await execute_tool_calls(self, calls)
```

修复建议：
- 为 `dispatch` 增加 `tool_filter: ToolExpression | None` 参数。
- 在执行前对 `call.name` 对应元数据进行过滤，不符合时返回带错误信息的 `ToolResult`。

## 4. `dispatch` 未做响应协议自动识别

文档描述通过响应指纹识别选择驱动，但当前实现要求明确 `driver_or_model` 并依赖别名映射。

证据：
```233:255:uni_tool/core/universe.py
    def _get_driver(self, driver_or_model: str) -> "BaseDriver":
        # Direct driver lookup
        if driver_or_model in self._drivers:
            return self._drivers[driver_or_model]

        # Alias lookup
        driver_name = self._driver_aliases.get(driver_or_model)
        if driver_name and driver_name in self._drivers:
            return self._drivers[driver_name]

        raise ValueError(f"No driver found for '{driver_or_model}'")
```

修复建议：
- 为驱动增加 `can_handle_response` 或类似能力判断方法，并在 `dispatch` 中自动选择驱动。
- 保留显式 `driver_or_model` 作为覆盖入口。

## 5. 多协议驱动缺失（仅注册 OpenAI）

文档描述支持 OpenAI/Claude/XML 等协议，当前默认仅注册 OpenAI 驱动。

证据：
```68:70:uni_tool/__init__.py
universe = Universe()
universe.register_driver("openai", OpenAIDriver())
```

修复建议：
- 实现并注册 Anthropic/XML 等驱动。
- 为不同驱动定义统一的 `render`/`parse` 行为与可用性判断。

## 6. 中间件去重规则与文档不一致

文档描述通过 uid 或类名去重，但当前仅基于 uid，且默认 uid 含函数 id，导致同类中间件难以去重。

证据：
```104:109:uni_tool/core/models.py
    def model_post_init(self, __context: Any) -> None:
        """Generate uid from function name if not provided."""
        if not self.uid:
            func_name = getattr(self.func, "__name__", "anonymous")
            object.__setattr__(self, "uid", f"mw_{func_name}_{id(self.func)}")
```
```125:151:uni_tool/middlewares/base.py
def deduplicate_middlewares(
    middlewares: list[MiddlewareObj],
) -> list[MiddlewareObj]:
    """
    Deduplicate middlewares by uid.
    """
    seen: dict[str, int] = {}
    result: list[MiddlewareObj] = []

    for mw in middlewares:
        if mw.uid and mw.uid in seen:
            # Replace the previous occurrence
            result[seen[mw.uid]] = mw
        else:
            if mw.uid:
                seen[mw.uid] = len(result)
            result.append(mw)
```

修复建议：
- 当 `uid` 未提供时使用稳定的类名/函数名作为 uid（避免包含 `id()`）。
- 或在去重逻辑中加入基于 `func.__qualname__` 或类名的回退规则。

## 7. `bind` 装饰器缺少 `exclude` 与 `middlewares` 支持

文档描述 `bind` 支持排除方法与传入中间件，但当前仅支持 `prefix` 与 `tags`。

证据：
```20:71:uni_tool/decorators/bind.py
def create_bind_decorator(
    universe: "Universe",
    *,
    prefix: Optional[str] = None,
    tags: Optional[Set[str]] = None,
) -> Callable[[type], type]:
    """
    Create a bind decorator bound to a specific Universe instance.
    """
    def decorator(cls: type) -> type:
        instance = cls()

        for method_name in dir(instance):
            if method_name.startswith("_"):
                continue

            method = getattr(instance, method_name)
            ...
            metadata = ToolMetadata(
                name=tool_name,
                description=extract_description(method),
                func=method,
                is_async=inspect.iscoroutinefunction(method),
                parameters_model=parameters_model,
                injected_params=injected_params,
                tags=tags or set(),
                middlewares=[],
            )
```

修复建议：
- 为 `bind` 增加 `exclude` 与 `middlewares` 参数。
- 在注册时将 `middlewares` 透传到 `ToolMetadata.middlewares`。

## 8. 参数注入与校验顺序（已按实现修订文档）

文档已更新为先校验再注入，与当前实现一致。

证据：
```45:66:uni_tool/core/execution.py
    async def final_handler(call: ToolCall) -> Any:
        # First, validate LLM-provided arguments with Pydantic model
        if metadata.parameters_model:
            validated = metadata.parameters_model(**call.arguments)
            validated_args = validated.model_dump()
        else:
            validated_args = dict(call.arguments)

        # Then inject context values (these are NOT in the Pydantic model)
        arguments = inject_context_values(
            validated_args,
            call.context,
            metadata.injected_params,
            call.name,
        )
```

处理：
- 已更新 `docs/architecture.md` 中的执行顺序说明。

## 9. 执行阶段并行策略不一致

文档描述 `dispatch` 内部并行执行，当前实现顺序执行。

证据：
```178:198:uni_tool/core/execution.py
async def execute_tool_calls(
    universe: "Universe",
    calls: List[ToolCall],
) -> List[ToolResult]:
    """
    Execute multiple tool calls.

    Currently executes sequentially. Parallel execution can be added later.
    """
    results = []
    for call in calls:
        result = await execute_single_tool(universe, call)
        results.append(result)
    return results
```

修复建议：
- 使用 `asyncio.gather` 并行执行工具调用，并保留顺序稳定性。
- 对共享资源与上下文隔离策略进行保护，避免并发副作用。
