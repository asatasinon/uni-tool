<!--
Sync Impact Report:
- Version: 0.2.0 -> 0.2.1
- Principles Refined:
  - Technical Standards (Explicit reference to CLAUDE.md for commands)
  - Development Workflow (Added Workflow Automation)
- Sections Updated:
  - Technical Standards
  - Development Workflow
- Templates Status: ✅ Verified
-->

# UniTools SDK 项目章程

## 核心原则

### I. 协议无关性 (Protocol Agnosticism)
核心逻辑 **必须** 与任何特定 LLM 提供商的协议（如 OpenAI, Anthropic）解耦。所有协议特定的转换 **必须** 发生在驱动层（Driver Layer）。Universe 作为统一的控制平面，不应包含特定模型的硬编码逻辑。

### II. 纵深防御 (Defense in Depth)
执行 **必须** 通过多层防御系统：Query 用于工具筛选，Filter 用于权限验证，Middleware 用于运行时隔离。严禁绕过这些安全层直接执行工具。

### III. 通过依赖注入实现上下文隔离 (Context Isolation via Dependency Injection)
敏感上下文（如用户 ID、Token）**必须** 在运行时使用 `Injected` 模式注入。工具 **必须** 避免将敏感数据作为直接参数暴露给 LLM。LLM 仅应感知业务参数。

### IV. 基于中间件的治理 (Middleware-Based Governance)
横切关注点（日志、认证、限流等）**必须** 实现为独立的中间件（Middlewares）。核心业务逻辑 **必须** 保持纯净，不包含治理逻辑。支持全局、作用域和工具级中间件。

## 技术标准

*   **语言版本**: Python 3.13+
*   **核心框架**: 必须使用 AsyncIO 处理所有 I/O 密集型操作。
*   **数据验证**: 必须使用 Pydantic 进行所有数据模型定义和运行时参数校验。
*   **类型安全**: 要求核心库具有 100% 的类型提示（Type Hinting）覆盖率。
*   **包管理**: 必须使用 `uv` 进行依赖管理和虚拟环境管理。禁止使用 `pip` 直接安装全局包。
*   **开发命令**: 必须遵循 `CLAUDE.md` 中定义的标准命令进行开发、测试和发布。
*   **风格**: 遵循 PEP 8 规范，使用现代 Python 特性。

## 开发工作流

*   **规范驱动 (Spec-Driven)**: 所有新功能 **必须** 遵循 `/speckit` 工作流（Init -> Spec -> Plan -> Tasks -> Impl）。
*   **测试驱动 (Test-Driven)**: 核心逻辑必须有单元测试覆盖。新的 Driver 实现必须通过契约测试。
*   **工作流自动化 (Workflow Automation)**: 开发过程中必须利用 `CLAUDE.md` 提供的自动化命令（如 `test-expression`, `test-middleware`）来确保验证的一致性。
*   **文档**: 公共 API 必须包含清晰的文档字符串（Docstrings）。

## 治理

此章程优先于所有其他实践指南。

*   **架构变更**: 对 `Universe` 核心类或 `Driver` 抽象基类的修改需要经过详细的设计审查（Design Review）。
*   **驱动兼容性**: 新引入的 Driver 必须证明与标准工具定义的兼容性达到 90% 以上。
*   **合规性**: 所有 PR 必须在合并前验证是否符合本章程规定的原则。

**版本**: 0.2.1 | **批准日期**: 2026-01-14 | **最后修正**: 2026-01-14
