# 实施计划: ToolExpression 增强

**分支**: `003-enhance-tool-expr` | **日期**: 2026-01-19 | **规范**: [specs/003-enhance-tool-expr/spec.md](spec.md)
**输入**: 来自 `/specs/003-enhance-tool-expr/spec.md` 的功能规范

**注意**: 此模板由 `/speckit.plan` 命令填充. 执行工作流程请参见 `.specify/templates/commands/plan.md`.

## 摘要

本计划实现 ToolExpression 的 DSL 字符串化与解析（基于 Lark），并在 Universe 支持直接接收字符串过滤条件，补充 `^tool_.*` 与 `` `tool_name` `` 的 DSL 简写。新增表达式诊断 Trace 以解释匹配路径与失败原因，同时提供表达式简化能力（去重、扁平化、双重否定消除）以降低匹配开销。

## 技术背景

<!--
  需要操作: 将此部分内容替换为项目的技术细节.
  此处的结构以咨询性质呈现, 用于指导迭代过程.
-->

**语言/版本**: Python 3.13+
**主要依赖**:
- `pydantic>=2.10`
- `docstring-parser>=0.17`
- `lark` (新增, DSL 解析)
**存储**: N/A (SDK 本身不涉及持久化存储)
**测试**: `pytest`, `pytest-asyncio`
**目标平台**: 跨平台 (Linux/macOS/Windows)
**项目类型**: Python SDK / Library
**性能目标**: 通过表达式简化降低匹配开销（规范未定义量化指标）
**约束条件**:
- DSL 解析必须使用 Lark
- 过滤条件与匹配大小写敏感
- 标签与名称不允许包含空格或 DSL 关键字符
**规模/范围**: 规范未定义明确规模指标

## 章程检查

*门控: 必须在阶段 0 研究前通过. 阶段 1 设计后重新检查. *

- [x] **协议无关性**: DSL 解析与表达式逻辑不依赖特定 LLM 协议。
- [x] **纵深防御**: 过滤与中间件路径保持原有 Query/Filter/Middleware 分层。
- [x] **依赖注入**: 解析与诊断不触及 Injected 机制与上下文注入路径。
- [x] **中间件治理**: 诊断与简化为表达式能力，不绕过中间件治理。
- [x] **技术栈合规**: Python 3.13+、AsyncIO、Pydantic、uv 管理依赖。

## 项目结构

### 文档(此功能)

```
specs/003-enhance-tool-expr/
├── plan.md              # 此文件 (/speckit.plan 命令输出)
├── research.md          # 阶段 0 输出 (/speckit.plan 命令)
├── data-model.md        # 阶段 1 输出 (/speckit.plan 命令)
├── quickstart.md        # 阶段 1 输出 (/speckit.plan 命令)
├── contracts/           # 阶段 1 输出 (/speckit.plan 命令)
└── tasks.md             # 阶段 2 输出 (/speckit.tasks 命令 - 非 /speckit.plan 创建)
```

### 源代码(仓库根目录)
<!--
  需要操作: 将下面的占位符树结构替换为此功能的具体布局.
  删除未使用的选项, 并使用真实路径(例如: apps/admin、packages/something)扩展所选结构.
  交付的计划不得包含选项标签.
-->

```
uni_tool/
├── core/
│   ├── expressions.py          # ToolExpression 与逻辑运算
│   ├── universe.py             # Universe 入口，字符串过滤解析
│   ├── errors.py               # 解析错误与诊断异常
│   └── expression_parser.py    # DSL 解析器 (新增)
├── filters/
│   └── __init__.py             # Tag/Prefix/ToolName 表达式
└── utils/
    └── docstring.py

tests/
├── unit/
│   ├── test_expression.py
│   ├── test_expression_parser.py
│   └── test_expression_trace.py
└── integration/
```

**结构决策**: 保持现有 Python SDK 结构，在 `core/` 增加解析与诊断模块，并扩展现有单元测试覆盖 DSL、诊断与简化。

## 复杂度跟踪

*仅在章程检查有必须证明的违规时填写*

| 违规 | 为什么需要 | 拒绝更简单替代方案的原因 |
|-----------|------------|-------------------------------------|
| (无) | | |
