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
- [ ] **设计审查**: `Universe` 与 `Driver` 抽象变更完成设计审查并记录结论。

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
