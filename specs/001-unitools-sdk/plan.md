# 实施计划: UniTools SDK

**分支**: `001-unitools-sdk` | **日期**: 2026-01-14 | **规范**: [specs/001-unitools-sdk/spec.md](spec.md)
**输入**: 来自 `/specs/001-unitools-sdk/spec.md` 的功能规范

**注意**: 此模板由 `/speckit.plan` 命令填充. 执行工作流程请参见 `.specify/templates/commands/plan.md`.

## 摘要

本计划旨在实现 UniTools SDK 的核心运行时 `Universe` 及其周边生态。系统将采用 "洋葱模型" 中间件架构，通过 `Driver` 层实现对 LLM 协议的解耦。核心功能包括基于 Pydantic 的元数据管理、基于装饰器的工具注册、依赖注入机制以及全异步的执行流水线。此外，还将内置审计、监控和告警等治理能力。

## 技术背景

<!--
  需要操作: 将此部分内容替换为项目的技术细节.
  此处的结构以咨询性质呈现, 用于指导迭代过程.
-->

**语言/版本**: Python 3.13+
**主要依赖**: 
- `pydantic>=2.0` (数据验证与 Schema 生成)
- `docstring_parser` (文档字符串解析)
**存储**: N/A (SDK 本身不涉及持久化存储，但支持通过 Driver/Middleware 扩展)
**测试**: `pytest`, `pytest-asyncio`
**目标平台**: 跨平台 (Linux/macOS/Windows)
**项目类型**: Python SDK / Library
**性能目标**: 极低的运行时开销 (Middleware 链)，原生 AsyncIO 支持以处理高并发 I/O。
**约束条件**: 
- 严格遵循类型提示 (100% Type Hinting)
- 零第三方重型依赖 (保持轻量)
- 必须通过 `uv` 管理依赖
**规模/范围**: 核心库代码量预计 < 2000 行，支持注册数百个工具。

## 章程检查

*门控: 必须在阶段 0 研究前通过. 阶段 1 设计后重新检查. *

- [x] **协议无关性**: 架构中 Driver 层明确负责协议转换，Universe 核心无硬编码。
- [x] **纵深防御**: Spec 中包含 Query (筛选) -> Filter (权限) -> Middleware (运行时) 三层防御。
- [x] **依赖注入**: Spec 明确要求实现 `Injected` 机制，敏感参数不暴露给 LLM。
- [x] **中间件治理**: Spec 采用了洋葱模型，且 FR-013/014/015 (审计/监控/告警) 将通过中间件实现。
- [x] **技术栈合规**: 计划使用 Python 3.13+, AsyncIO, Pydantic, uv。

## 项目结构

### 文档(此功能)

```
specs/001-unitools-sdk/
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
├── __init__.py            # 导出 Universe 类及默认实例 `universe`
├── core/                  # 核心逻辑
│   ├── universe.py        # Universe 单例 (Singleton Implementation)
│   ├── models.py          # ToolMetadata, ToolCall 等 Pydantic 模型
│   ├── execution.py       # 流水线执行逻辑
│   └── errors.py          # 统一异常定义
├── decorators/            # 用户接口
│   ├── tool.py            # @tool 装饰器
│   └── bind.py            # @bind 装饰器
├── drivers/               # 协议驱动
│   ├── base.py            # BaseDriver 接口
│   └── openai.py          # OpenAIDriver 实现
├── middlewares/           # 内置中间件
│   ├── base.py            # Middleware 协议
│   ├── audit.py           # 审计中间件
│   ├── monitor.py         # 监控中间件
│   └── logging.py         # 日志中间件
└── utils/                 # 工具函数
    ├── injection.py       # 依赖注入解析
    └── docstring.py       # 文档解析

tests/
├── unit/
├── integration/
└── conftest.py
```

**结构决策**: 采用标准的 Python 包结构，`core` 包含核心运行时，`drivers` 和 `middlewares` 模块化扩展。

## 复杂度跟踪

*仅在章程检查有必须证明的违规时填写*

| 违规 | 为什么需要 | 拒绝更简单替代方案的原因 |
|-----------|------------|-------------------------------------|
| (无) | | |
