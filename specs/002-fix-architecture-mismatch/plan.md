# 实施计划: 架构一致性对齐

**分支**: `002-fix-architecture-mismatch` | **日期**: 2026-01-16 | **规范**: [specs/002-fix-architecture-mismatch/spec.md](spec.md)
**输入**: 来自 `/specs/002-fix-architecture-mismatch/spec.md` 的功能规范

**注意**: 此模板由 `/speckit.plan` 命令填充. 执行工作流程请参见 `.specify/templates/commands/plan.md`.

## 摘要

本计划聚焦于修复当前实现与 `docs/architecture.md` 的关键不一致项，补齐 `ToolSet`、协议协商与自动识别、`dispatch` 的安全过滤、驱动多协议支持、中间件去重规则、`bind` 排除与中间件配置，以及多工具调用的并行执行与顺序稳定性。工具过滤统一为 `ToolExpression`，工具名过滤通过 `ToolName(ToolExpression)` 实现。实现方式以 Driver 层能力协商与响应指纹匹配为核心，确保 Universe 核心保持协议无关，同时遵循纵深防御与上下文隔离原则。

## 技术背景

<!--
  需要操作: 将此部分内容替换为项目的技术细节.
  此处的结构以咨询性质呈现, 用于指导迭代过程.
-->

**语言/版本**: Python 3.13+
**主要依赖**:
- `pydantic>=2.10.0` (数据模型与校验)
- `docstring-parser>=0.17.0` (文档字符串解析)
**存储**: N/A (SDK 不包含持久化存储)
**测试**: `pytest`, `pytest-asyncio`
**目标平台**: macOS / Linux / Windows
**项目类型**: Python SDK / Library
**性能目标**: 在包含至少 4 个工具调用的响应中，`dispatch` 并行执行耗时较顺序基线降低 ≥ 30% (SC-002)
**约束条件**:
- 必须使用 AsyncIO 处理 I/O 密集操作
- 必须使用 Pydantic 进行数据校验
- 必须使用 `uv` 管理依赖与虚拟环境
- 核心库保持 100% 类型提示覆盖
**规模/范围**: 仅对齐不一致项清单中列出的行为 (见 `specs/002-fix-architecture-mismatch/spec.md`)

## 章程检查

*门控: 必须在阶段 0 研究前通过. 阶段 1 设计后重新检查. *

- [x] **协议无关性**: 通过 Driver 能力协商与响应识别实现协议差异，Universe 核心不绑定协议细节。
- [x] **纵深防御**: `dispatch` 恢复 Query -> Filter -> Middleware 的执行链路。
- [x] **依赖注入**: 保持 `Injected` 作为敏感上下文注入机制。
- [x] **中间件治理**: 中间件去重与配置仍由中间件层管理。
- [x] **技术栈合规**: Python 3.13+、AsyncIO、Pydantic、uv、pytest。
- [x] **设计审查**: `Universe` 与 `Driver` 抽象变更完成设计审查并记录结论。

## 设计审查记录

**审查日期**: 2026-01-16
**审查结论**: 通过

### 关键设计决策

1. **`Universe.__getitem__` 语义变更**: 
   - `str` 参数视为 Tag 过滤，返回 `ToolSet`
   - `get(name)` 保留为按名称获取单个工具的入口
   - **理由**: 与架构文档保持一致，同时保留显式工具访问能力

2. **`ToolSet.render` 协商机制**:
   - 接受模型名或驱动名字符串
   - 驱动名直接使用该驱动；模型名生成 `ModelProfile` 并通过 `can_handle` 评分择优
   - **理由**: 支持显式与自动协商双通道

3. **驱动层能力扩展**:
   - `BaseDriver` 新增 `can_handle(profile)` 和 `can_handle_response(response)` 评分接口
   - 返回 0-100 分数，0 表示不支持，100 表示最佳匹配
   - **理由**: 将协议差异下沉到驱动层，保持 Universe 协议无关

4. **`dispatch` 安全过滤**:
   - `tool_filter` 参数仅支持 `ToolExpression`
   - 工具名过滤通过 `ToolName(ToolExpression)` 实现统一入口
   - 被拒绝的调用返回带 `error_code` 的 `ToolResult`，不执行工具函数
   - **理由**: 统一过滤规则，避免多分支行为差异

5. **中间件去重标识**:
   - `MiddlewareObj.uid` 默认使用 `__qualname__` 生成稳定标识
   - 相同 uid 后注册的中间件覆盖先注册的
   - **理由**: 支持中间件更新与覆盖，避免 `id()` 的不稳定性

6. **并行执行与上下文隔离**:
   - `execute_tool_calls` 使用 `asyncio.gather` 并行执行
   - 每个 `ToolCall.context` 独立拷贝
   - **理由**: 满足性能目标（≥30% 提升）与上下文隔离要求

## 项目结构

### 文档(此功能)

```
specs/002-fix-architecture-mismatch/
├── plan.md              # 此文件 (/speckit.plan 命令输出)
├── research.md          # 阶段 0 输出 (/speckit.plan 命令)
├── data-model.md        # 阶段 1 输出 (/speckit.plan 命令)
├── quickstart.md        # 阶段 1 输出 (/speckit.plan 命令)
├── contracts/           # 阶段 1 输出 (/speckit.plan 命令)
└── tasks.md             # 阶段 2 输出 (/speckit.tasks 命令 - 非 /speckit.plan 创建)
```

### 源代码(仓库根目录)

```
uni_tool/
├── __init__.py
├── core/
│   ├── universe.py        # ToolSet / 协议协商 / dispatch 过滤与识别
│   ├── models.py          # ToolMetadata / ToolCall / ToolResult
│   ├── execution.py       # 并行执行与上下文隔离
│   └── errors.py
├── decorators/
│   ├── bind.py            # exclude / middlewares 支持
│   └── tool.py
├── drivers/
│   ├── base.py            # 协议驱动基类能力扩展
│   ├── openai.py
│   ├── anthropic.py       # 新增
│   ├── xml.py             # 新增
│   └── markdown.py        # 新增
├── middlewares/
│   ├── base.py            # 去重逻辑与稳定 uid
│   ├── audit.py
│   ├── monitor.py
│   └── logging.py
└── utils/
    ├── injection.py
    └── docstring.py

tests/
├── unit/
│   ├── test_expression.py
│   ├── test_middleware.py
│   ├── test_registry.py
│   └── test_openai_driver.py
└── integration/
    ├── test_execution.py
    └── test_full_flow.py
```

**结构决策**: 沿用现有 Python SDK 目录结构，核心逻辑集中在 `uni_tool/core`，协议差异下沉到 `uni_tool/drivers`，并通过测试目录覆盖关键行为。

## 复杂度跟踪

*仅在章程检查有必须证明的违规时填写*

| 违规 | 为什么需要 | 拒绝更简单替代方案的原因 |
|-----------|------------|-------------------------------------|
| (无) | | |
