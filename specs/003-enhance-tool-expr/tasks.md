---
description: "功能实现任务列表"
---

# 任务: ToolExpression 增强

**输入**: 来自 `/specs/003-enhance-tool-expr/` 的设计文档
**前置条件**: plan.md(必需)、spec.md(用户故事必需)、research.md、data-model.md、contracts/、quickstart.md

**测试**: 本任务包含测试任务（规范要求独立测试）。

**组织结构**: 任务按用户故事分组, 以便每个故事能够独立实施和测试.

## 格式: `[ID] [P?] [Story] 描述`
- **[P]**: 可以并行运行(不同文件, 无依赖关系)
- **[Story]**: 此任务属于哪个用户故事(例如: US1、US2、US3)
- 在描述中包含确切的文件路径

## 路径约定
- 该功能为单一项目, 源码位于仓库根目录下的 `uni_tool/` 与 `tests/`

## 阶段 1: 设置(共享基础设施)

**目的**: 项目初始化和基本依赖准备

- [X] T001 在 `pyproject.toml` 与 `uv.lock` 中添加 `lark` 依赖(通过 `uv add lark`)

---

## 阶段 2: 基础(阻塞前置条件)

**目的**: 在任何用户故事可以实施之前必须完成的核心基础设施

**⚠️ 关键**: 在此阶段完成之前, 无法开始任何用户故事工作

- [X] T002 在 `uni_tool/core/expressions.py` 中扩展 `ToolExpression` 接口, 新增 `to_dsl()`/`diagnose()`/`simplify()` 抽象方法
- [X] T003 [P] 在 `uni_tool/core/errors.py` 中新增 `ExpressionParseError`, 用 Pydantic `BaseModel` 承载 `message/line/column/context`

**检查点**: 基础就绪 - 现在可以开始并行实施用户故事

---

## 阶段 3: 用户故事 1 - 表达式字符串化与解析(DSL)(优先级: P2)🎯 MVP

**目标**: 提供 DSL 字符串化与解析能力, Universe 可直接接收 DSL 字符串过滤条件.

**独立测试**: parser 测试覆盖解析、简写与错误场景, Universe 字符串过滤与表达式对象一致.

### 用户故事 1 的测试 ⚠️

**注意: 先编写这些测试, 确保在实施前它们失败**

- [X] T004 [P] [US1] 在 `tests/unit/test_expression_parser.py` 中覆盖 DSL 解析/优先级/简写/非法标识符/非法 `^` 简写/深度过深/错误细节(line/column/context)
- [X] T005 [P] [US1] 在 `tests/unit/test_expression.py` 中验证 Universe 接收 DSL 字符串与表达式对象结果一致, 并校验大小写敏感匹配

### 用户故事 1 的实施

- [X] T006 [US1] 在 `uni_tool/core/expression_parser.py` 中实现 Lark 语法、Transformer、标识符约束、`^tool_.*` 简写校验、深度限制与错误映射
- [X] T007 [US1] 在 `uni_tool/core/universe.py` 中让 `__getitem__` 解析 DSL 字符串并处理 `ExpressionParseError`
- [X] T008 [US1] 在 `uni_tool/core/expressions.py` 中实现 `And`/`Or`/`Not` 的 `to_dsl()`(含括号与优先级)
- [X] T009 [US1] 在 `uni_tool/filters/__init__.py` 中实现 `Tag`/`Prefix`/`ToolName` 的 `to_dsl()`

**检查点**: 此时, 用户故事 1 应该完全功能化且可独立测试

---

## 阶段 4: 用户故事 2 - 表达式诊断与调试(优先级: P2)

**目标**: 提供可读的诊断 Trace, 解释命中路径与失败原因.

**独立测试**: 对特定表达式调用诊断方法, 验证 Trace 结构与失败原因.

### 用户故事 2 的测试 ⚠️

- [X] T010 [P] [US2] 在 `tests/unit/test_expression_trace.py` 中覆盖诊断路径与失败原因

### 用户故事 2 的实施

- [X] T011 [US2] 在 `uni_tool/core/expressions.py` 中定义 Pydantic `ExpressionTrace` 并实现组合表达式的 `diagnose()` 递归
- [X] T012 [US2] 在 `uni_tool/filters/__init__.py` 中实现 `Tag`/`Prefix`/`ToolName` 的 `diagnose()`

**检查点**: 此时, 用户故事 1 和 2 都应该独立运行

---

## 阶段 5: 用户故事 3 - 表达式优化(优先级: P3)

**目标**: 自动简化低效表达式, 降低匹配开销.

**独立测试**: 构造冗余表达式, 断言简化后的表达式结构.

### 用户故事 3 的测试 ⚠️

- [X] T013 [P] [US3] 在 `tests/unit/test_expression.py` 中覆盖简化规则(去重/扁平化/双重否定)

### 用户故事 3 的实施

- [X] T014 [US3] 在 `uni_tool/core/expressions.py` 中实现 `simplify()` 规则并保持语义等价
- [X] T015 [US3] 在 `uni_tool/filters/__init__.py` 中实现 `simplify()`(原子表达式返回自身)

**检查点**: 所有用户故事现在应该独立功能化

---

## 依赖关系与执行顺序

### 阶段依赖关系

- **设置(阶段 1)**: 无依赖关系 - 可立即开始
- **基础(阶段 2)**: 依赖于设置完成 - 阻塞所有用户故事
- **用户故事(阶段 3+)**: 都依赖于基础阶段完成
  - 建议完成顺序: US1 → US2 → US3

### 用户故事依赖关系

- **用户故事 1(P2)**: 依赖基础阶段, 可作为 MVP 先行完成
- **用户故事 2(P2)**: 依赖基础阶段, 与 US1 无强依赖但共享表达式文件
- **用户故事 3(P3)**: 依赖基础阶段, 可在 US1/US2 后实施

### 每个用户故事内部

- 测试必须在实施前编写并失败
- 解析/诊断/简化逻辑在表达式核心实现后再扩展到过滤器实现

### 并行机会

- 标记为 [P] 的测试任务可以并行运行
- 标记为 [P] 的错误类型与验证任务可以并行运行

---

## 并行示例: 用户故事 1

```bash
# 一起启动用户故事 1 的测试:
任务: "在 tests/unit/test_expression_parser.py 中覆盖 DSL 解析/优先级/简写/错误场景"
任务: "在 tests/unit/test_expression.py 中验证 Universe 接收 DSL 字符串与表达式对象结果一致"
```

---

## 并行示例: 用户故事 2

```bash
# 启动用户故事 2 的测试:
任务: "在 tests/unit/test_expression_trace.py 中覆盖诊断路径与失败原因"
```

---

## 并行示例: 用户故事 3

```bash
# 启动用户故事 3 的测试:
任务: "在 tests/unit/test_expression.py 中覆盖简化规则(去重/扁平化/双重否定)"
```

---

## 实施策略

### 仅 MVP(仅用户故事 1)

1. 完成阶段 1: 设置
2. 完成阶段 2: 基础(关键 - 阻塞所有故事)
3. 完成阶段 3: 用户故事 1
4. **停止并验证**: 独立测试用户故事 1

### 增量交付

1. 完成设置 + 基础 → 基础就绪
2. 添加用户故事 1 → 独立测试 → MVP 完成
3. 添加用户故事 2 → 独立测试 → 诊断可用
4. 添加用户故事 3 → 独立测试 → 简化生效

---

## 注意事项

- [P] 任务 = 不同文件, 无依赖关系
- [Story] 标签将任务映射到特定用户故事以实现可追溯性
- 每个用户故事应该独立可完成和可测试
- 在实施前验证测试失败
- 避免: 模糊任务、相同文件冲突、破坏独立性的跨故事依赖
