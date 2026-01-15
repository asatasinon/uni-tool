# UniTools SDK

---

## 1. 设计愿景
UniTools 是一个为大模型（LLM）应用设计的**全栈工具治理框架**。它采用了 **“Universe（统一宇宙）”** 模式，将业务逻辑代码与 LLM 的协议细节彻底解耦，提供了一套类似操作系统驱动程序的管理机制。

**核心能力：**
*   **统一入口**：单点管理所有工具与配置。
*   **协议自适应**：自动协商 LLM 协议（OpenAI/Claude/XML），无需硬编码。
*   **流式筛选**：类 SQL 的工具集查询语法。
*   **洋葱模型**：支持去重、隔离、上下文共享的中间件流水线。
*   **依赖注入**：运行时自动注入敏感参数，对 LLM 隐藏实现细节。

---

## 2. 核心组件架构

### 2.1 组件关系图
```mermaid
[Universe] 
  ├── Registry (元数据存储)
  ├── Middlewares (全局/规则级中间件)
  └── Drivers (协议驱动池)
       ├── OpenAIDriver
       ├── AnthropicDriver
       └── XMLDriver

[开发阶段] -> Universe.tool/bind -> [Registry]
[Prompt阶段] -> Universe[Query] -> ToolSet -> Driver.render() -> [JSON/XML Schema]
[执行阶段] -> Universe.dispatch() -> Filter -> Middleware Chain -> [Function Execution]
```

---

## 3. 组件详细设计与伪代码

### 3.1 `Universe` (核心控制台)
全单例或上下文管理器，负责协调所有子系统。

```python
class Universe:
    def __init__(self):
        self._registry: Dict[str, ToolMetadata] = {}
        self._global_middlewares: List[MiddlewareObj] = []
        self._scoped_middlewares: List[Tuple[ToolExpression, MiddlewareObj]] = []
        self._drivers: List[BaseDriver] = [OpenAIDriver(), XMLDriver(), ...]

    # --- 注册类接口 ---
    def tool(self, name=None, tags=None, middlewares=None):
        """函数装饰器：注册单个工具"""
        def decorator(func):
            meta = ToolMetadata.from_func(func, name, tags, middlewares)
            self._registry[meta.name] = meta
            return func
        return decorator

    def bind(self, prefix="", tags=None, exclude=None, middlewares=None):
        """类装饰器：批量绑定类方法"""
        def decorator(cls):
            instance = cls() # 自动实例化
            for method_name in dir(instance):
                # 扫描 public 方法，自动继承 tags 和 middlewares
                # 注册到 self._registry
                pass
            return cls
        return decorator

    # --- 中间件配置 ---
    def use(self, middleware, scope: ToolExpression = None, critical=True):
        """挂载中间件，支持指定作用域和是否核心(critical)"""
        mw_obj = MiddlewareObj(middleware, critical=critical)
        if scope:
            self._scoped_middlewares.append((scope, mw_obj))
        else:
            self._global_middlewares.append(mw_obj)

    # --- 查询/筛选入口 ---
    def __getitem__(self, query: Union[str, ToolExpression]) -> 'ToolSet':
        """流式筛选：u[Tag('finance')]"""
        if isinstance(query, str): query = Tag(query)
        matched_tools = [m for m in self._registry.values() if query.matches(m)]
        return ToolSet(matched_tools, self._drivers)

    # --- 执行入口 ---
    async def dispatch(self, response: Any, context: dict = None, tool_filter: ToolExpression = None):
        """
        全自动执行入口：
        1. Fingerprinting: 识别 response 类型。
        2. Parsing: 提取 ToolCall。
        3. Filter: 安全检查。
        4. Execution: 运行中间件链。
        """
        # 1. 自动选择驱动并解析
        driver = self._select_driver_by_response(response)
        tool_calls = driver.parse(response)

        # 2. 并行执行
        tasks = []
        for call in tool_calls:
            # 3. 安全过滤 (Filter)
            meta = self._registry.get(call.name)
            if tool_filter and not tool_filter.matches(meta):
                tasks.append(ToolResult.error("Permission Denied"))
                continue
            
            # 4. 注入初始 Context
            call.context.update(context or {})
            
            # 5. 启动流水线
            tasks.append(self._run_pipeline(call, meta))
        
        return await asyncio.gather(*tasks)
```

### 3.2 `ToolMetadata` (元数据载体)
存储工具的静态属性和运行时所需的注入信息。

```python
class ToolMetadata:
    def __init__(self, name, fn, params_model, tags, local_middlewares):
        self.name = name
        self.fn = fn
        self.tags = set(tags or [])
        self.middlewares = local_middlewares or [] # 工具级中间件
        self.parameters_model = params_model       # Pydantic Model
        self.injected_params = {}                  # {param_name: context_key}

    @classmethod
    def from_func(cls, func, ...):
        # 1. 解析 Annotated[T, Injected('key')]
        # 2. 解析 Docstring
        # 3. 创建 Pydantic Model (剔除 Injected 参数)
        pass
```

### 3.3 `ToolExpression` (逻辑表达式引擎)
实现 `Query` (筛选) 和 `Filter` (校验) 的底层逻辑。

```python
class ToolExpression(ABC):
    @abstractmethod
    def matches(self, meta: ToolMetadata) -> bool: pass

    # 运算符重载实现组合逻辑
    def __and__(self, other): return AndExpr(self, other)
    def __or__(self, other): return OrExpr(self, other)
    def __invert__(self): return NotExpr(self)

class Tag(ToolExpression):
    def matches(self, meta): return self.tag in meta.tags

class Prefix(ToolExpression):
    def matches(self, meta): return meta.name.startswith(self.prefix)
```

### 3.4 `ToolSet` (工具集合与渲染)
`u[...]` 操作的返回结果，负责向 LLM 展示。

```python
class ToolSet:
    def render(self, model_name: str):
        """根据模型名自动协商协议并渲染"""
        # 1. 生成模型画像
        profile = ModelProfile.from_name(model_name)
        # 2. 驱动竞争
        best_driver = max(self.drivers, key=lambda d: d.can_handle(profile))
        # 3. 渲染
        return best_driver.render(self.tools)

    def to_markdown(self):
        """生成文档"""
        pass
```

### 3.5 `Driver` (自适应驱动)
负责具体的协议转换。

```python
class BaseDriver:
    def can_handle(self, profile: ModelProfile) -> int:
        """返回 0-100 的匹配分"""
        pass
    
    def render(self, tools: List[ToolMetadata]) -> Any:
        """生成 Schema (JSON/XML)"""
        pass

    def parse(self, response: Any) -> List[ToolCall]:
        """解析 LLM 响应"""
        pass

class OpenAIDriver(BaseDriver):
    def can_handle(self, p): 
        return 100 if p.capability == 'FC_NATIVE' else 0
    # ... 实现 render 和 parse ...
```

---

## 4. 执行核心设计：洋葱流水线

这是 `dispatch` 方法内部 `_run_pipeline` 的详细逻辑，包含**去重、上下文共享和异常隔离**。

```python
    async def _run_pipeline(self, call: ToolCall, meta: ToolMetadata):
        # 1. 组装中间件链 (Assembly)
        # 顺序：Global -> Scoped (匹配到的) -> Local (工具自带的)
        candidates = []
        candidates.extend(self._global_middlewares)
        candidates.extend([mw for scope, mw in self._scoped_middlewares if scope.matches(meta)])
        candidates.extend([MiddlewareObj(m) for m in meta.middlewares])

        # 2. 有序去重 (Deduplication)
        # 根据 Middleware 的 uid 或类名去重，保留优先级最高的
        chain_objs = self._deduplicate_middlewares(candidates)

        # 3. 终端处理器 (Terminal Handler)
        async def terminal_handler(ctx_call):
            # Pydantic 校验 (Validation)
            # 先校验 LLM 提供的参数，若失败抛出 ValidationError，由外层中间件捕获用于 Self-Correction
            validated_args = meta.parameters_model(**ctx_call.arguments)

            # 依赖注入 (Dependency Injection)
            # 校验通过后，再从 ctx_call.context 中提取数据填入 kwargs
            real_args = self._inject_dependencies(ctx_call, meta, validated_args)
            
            # 执行
            if meta.is_async:
                return await meta.fn(**real_args)
            else:
                return await asyncio.to_thread(meta.fn, **real_args)

        # 4. 递归包装 (Wrapping)
        handler = terminal_handler
        for mw_obj in reversed(chain_objs):
            # 使用 partial 绑定 next_handler
            # 增加异常隔离逻辑
            handler = self._wrap_middleware(mw_obj, handler)
            
        # 5. 触发执行
        return await handler(call)

    def _wrap_middleware(self, mw_obj, next_handler):
        async def wrapper(call):
            try:
                # 传递 context 是通过 call 对象引用的，天然共享
                return await mw_obj.func(call, next_handler)
            except Exception as e:
                if mw_obj.critical:
                    raise e # 核心中间件失败，中断流程
                else:
                    # 非核心中间件失败，记录日志，跳过该层，继续执行 next
                    logger.error(f"Middleware {mw_obj.uid} failed: {e}")
                    return await next_handler(call)
        return wrapper
```

---

## 5. 完整使用示例

### 5.1 初始化与中间件配置
```python
from unitools import Universe, Tag, Prefix, Injected, ToolResult

u = Universe()

# 全局中间件：非核心，挂了不影响业务
async def metrics_mw(call, next_h):
    print(f"Start: {call.name}")
    res = await next_h(call)
    print(f"End: {call.name}")
    return res

u.use(metrics_mw, critical=False)

# 规则中间件：仅针对 Finance 标签，核心
async def audit_mw(call, next_h):
    if "user_id" not in call.context:
        return ToolResult.error("Unauthorized") # 阻断执行
    return await next_h(call)

u.use(audit_mw, scope=Tag("finance"), critical=True)
```

### 5.2 工具注册 (含注入与类绑定)
```python
@u.bind(prefix="Bank__", tags=["finance"])
class BankService:
    def __init__(self):
        self.db = {"u1": 1000}

    # user 参数对 LLM 不可见，运行时自动从 context['uid'] 获取
    async def get_balance(self, user: Annotated[str, Injected("uid")]):
        """查询余额"""
        return self.db.get(user, 0)

    # 局部中间件：特定工具的特殊逻辑
    @u.tool(middlewares=[double_check_mw]) 
    async def transfer(self, to: str, amount: float):
        """转账"""
        return "ok"
```

### 5.3 导出与 Prompt 阶段 (Query)
```python
# 业务方：我只想要金融工具，且不包含内部接口
# 适配：自动识别 GPT-4o 并生成 JSON Schema
scope = Tag("finance") & ~Tag("internal")
tools_schema = u[scope].render("gpt-4o")

# 发送给 LLM...
```

### 5.4 执行与分发 (Dispatch)
```python
# 假设 LLM 返回了 response (可以是 OpenAI 对象，也可以是 XML 字符串)
# 外部系统将 uid 放入 context
context_data = {"uid": "u1"}

# 自动识别协议 -> 过滤 -> 执行流水线 -> 返回结果
results = await u.dispatch(
    response, 
    context=context_data, 
    tool_filter=scope # 复用 scope 作为安全防线
)
```

---

## 6. 设计总结

此方案通过以下机制实现了企业级的稳健性：

1.  **协议自适应**：Driver 模式消除了 `if model == 'gpt'` 的硬编码。
2.  **安全闭环**：`Query` 生成菜单，`Filter` 校验权限，`Injected` 隐藏参数，三层防护防止幻觉和攻击。
3.  **中间件治理**：通过 ID 去重防止重复执行，通过 `critical` 标志实现异常隔离，通过 `context` 实现数据穿透。
4.  **开发体验**：流式 API (`u[Tag & Tag]`) 提供了极致的开发效率和可读性。
