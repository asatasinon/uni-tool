# 任务: 架构一致性对齐

**输入**: 来自 `/specs/002-fix-architecture-mismatch/` 的设计文档
**前置条件**: plan.md(必需)、spec.md(用户故事必需)、research.md、data-model.md、contracts/

**测试**: 测试任务仅在功能规范中明确要求时才包含。

**组织结构**: 任务按用户故事分组, 以便每个故事能够独立实施和测试.

## 格式: `[ID] [P?] [Story] 描述`
- **[P]**: 可以并行运行(不同文件, 无依赖关系)
- **[Story]**: 此任务属于哪个用户故事(例如: US1、US2、US3)
- 在描述中包含确切的文件路径

## 路径约定
- 单一项目: 仓库根目录下的 `uni_tool/`、`tests/`

---

## 阶段 0: 设计审查(门控)

**目的**: 对 `Universe` 与 `Driver` 抽象变更进行设计审查

- [ ] T000 在 `specs/002-fix-architecture-mismatch/spec.md` 与 `specs/002-fix-architecture-mismatch/plan.md` 完成设计审查记录与结论

---

## 阶段 1: 设置(共享基础设施)

**目的**: 项目初始化和关键类型对齐

- [ ] T001 在 `uni_tool/core/models.py` 补齐 `ModelProfile` 数据结构并对齐 `ToolCall`/`ToolResult` 字段类型
- [ ] T002 在 `uni_tool/drivers/base.py` 增加 `can_handle`/`can_handle_response` 评分接口

---

## 阶段 2: 基础(阻塞前置条件)

**目的**: 在任何用户故事可以实施之前必须完成的核心基础设施

**⚠️ 关键**: 在此阶段完成之前, 无法开始任何用户故事工作

- [ ] T003 在 `uni_tool/core/models.py` 实现 `ToolName` 表达式与 `ToolFilter` 类型别名
- [ ] T004 在 `uni_tool/core/models.py` 与 `uni_tool/middlewares/base.py` 调整 `MiddlewareObj.uid` 默认生成规则为类名/函数名稳定值
- [ ] T005 在 `uni_tool/core/universe.py` 增加驱动评分选择的内部工具函数, 供 `render/dispatch` 共用

**检查点**: 基础就绪 - 现在可以开始并行实施用户故事

---

## 阶段 3: 用户故事 1 - 按标签获取并渲染工具集合(优先级: P1)🎯 MVP

**目标**: 通过标签筛选工具并依据模型能力渲染可用工具集合

**独立测试**: 使用含/不含标签的工具集并选择目标模型, 验证筛选结果与渲染协议正确性

### 用户故事 1 的实施

- [ ] T006 [US1] 在 `uni_tool/core/universe.py` 调整 `__getitem__` 对 `str` 走 Tag 过滤并返回 `ToolSet`, `get` 仅用于按名称获取
- [ ] T007 [P] [US1] 在 `uni_tool/core/models.py` 新增 `ToolSet` 数据类(包含 `tools/expression/drivers`)
- [ ] T008 [US1] 在 `uni_tool/core/universe.py` 实现 `ToolSet.render` 协商逻辑(模型名 -> `ModelProfile` -> `BaseDriver.can_handle`)
- [ ] T009 [US1] 在 `uni_tool/core/universe.py` 处理空标签过滤返回空集合且可安全渲染

**检查点**: 此时, 用户故事 1 应该完全功能化且可独立测试

---

## 阶段 4: 用户故事 2 - 安全过滤与协议自动识别的工具调度(优先级: P2)

**目标**: 调度时支持 ToolExpression 安全过滤并自动识别协议

**独立测试**: 构造包含允许与不允许工具调用的响应验证过滤; 使用不同协议响应验证自动识别与显式协议覆盖

### 用户故事 2 的实施

- [ ] T010 [US2] 在 `uni_tool/core/universe.py` 的 `dispatch` 增加 `tool_filter` 参数并应用 `ToolFilter`
- [ ] T011 [US2] 在 `uni_tool/core/universe.py` 支持未指定协议时基于 `can_handle_response` 自动识别, 识别失败返回错误结果但不中断调度
- [ ] T012 [P] [US2] 在 `uni_tool/drivers/openai.py` 实现 `can_handle`/`can_handle_response` 并对齐 `parse` 输出结构
- [ ] T013 [P] [US2] 在 `uni_tool/drivers/anthropic.py` 新增驱动实现 `render/parse/can_handle/can_handle_response`
- [ ] T014 [P] [US2] 在 `uni_tool/drivers/xml.py` 新增驱动实现 `render/parse/can_handle/can_handle_response`
- [ ] T015 [P] [US2] 在 `uni_tool/drivers/markdown.py` 新增驱动实现 `render/parse/can_handle/can_handle_response`
- [ ] T016 [US2] 在 `uni_tool/drivers/__init__.py` 导出新驱动并补充注册入口

**检查点**: 此时, 用户故事 2 应该独立可用且可独立测试

---

## 阶段 5: 用户故事 3 - 可配置绑定、中间件去重与多调用性能(优先级: P3)

**目标**: 绑定可排除/可配置中间件, 去重稳定, 多调用并行且顺序稳定

**独立测试**: 配置排除列表与中间件去重验证覆盖规则; 构造多调用响应验证并行执行与顺序稳定

### 用户故事 3 的实施

- [ ] T017 [US3] 在 `uni_tool/decorators/bind.py` 增加 `exclude`/`middlewares` 参数并传入 `ToolMetadata`
- [ ] T018 [US3] 在 `uni_tool/middlewares/base.py` 更新 `deduplicate_middlewares` 使用稳定 `uid` 覆盖逻辑
- [ ] T019 [US3] 在 `uni_tool/core/execution.py` 将 `execute_tool_calls` 改为 `asyncio.gather` 并保持结果顺序
- [ ] T020 [US3] 在 `uni_tool/core/execution.py` 为每个 `ToolCall.context` 创建独立拷贝以保证隔离

**检查点**: 所有用户故事现在应该独立功能化

---

## 阶段 N: 完善与横切关注点

**目的**: 影响多个用户故事的改进

- [ ] T021 运行 `uv run pytest tests/unit` 验证核心过滤、驱动协商与中间件去重的基线
- [ ] T022 在 `tests/contract/test_driver_contracts.py` 补充 OpenAI/Anthropic/XML/markdown 驱动契约测试
- [ ] T023 在 `tests/integration/test_execution.py` 增加并行执行性能基线与 ≥30% 提升断言
- [ ] T024 在 `tests/integration/test_full_flow.py` 增加协议自动识别成功率 100% 的用例
- [ ] T025 在 `tests/integration/test_full_flow.py` 增加工具过滤拒绝准确率 100% 的用例

---

## 依赖关系与执行顺序

### 阶段依赖关系

- **设计审查(阶段 0)**: 无依赖关系 - 必须先完成
- **设置(阶段 1)**: 依赖设计审查完成
- **基础(阶段 2)**: 依赖于设置完成 - 阻塞所有用户故事
- **用户故事(阶段 3+)**: 都依赖于基础阶段完成
  - 然后用户故事可以并行进行(如果有人员)
  - 或按优先级顺序进行(P1 → P2 → P3)
- **完善(最终阶段)**: 依赖于所有期望的用户故事完成

### 用户故事依赖关系

- **用户故事 1(P1)**: 可在基础(阶段 2)后开始 - 无其他故事依赖
- **用户故事 2(P2)**: 可在基础(阶段 2)后开始 - 可与 US1 集成但应独立可测试
- **用户故事 3(P3)**: 可在基础(阶段 2)后开始 - 可与 US1/US2 集成但应独立可测试

### 每个用户故事内部

- 模型/类型在服务之前
- 过滤与协商在调度之前
- 核心实现完成后才移至下一个优先级

### 并行机会

- 所有标记为 [P] 的基础任务可以并行运行
- 基础阶段完成后, 所有用户故事可以并行开始(如果团队容量允许)
- 用户故事中所有标记为 [P] 的驱动实现可以并行运行
- 不同用户故事可以由不同团队成员并行处理

---

## 并行示例: 用户故事 1

```bash
# 一起启动用户故事 1 的并行任务:
任务: "在 uni_tool/core/models.py 新增 ToolSet 数据类(包含 tools/expression/drivers)"
```

---

## 并行示例: 用户故事 2

```bash
# 一起启动用户故事 2 的驱动实现:
任务: "在 uni_tool/drivers/openai.py 实现 can_handle/can_handle_response 并对齐 parse 输出结构"
任务: "在 uni_tool/drivers/anthropic.py 新增驱动实现 render/parse/can_handle/can_handle_response"
任务: "在 uni_tool/drivers/xml.py 新增驱动实现 render/parse/can_handle/can_handle_response"
任务: "在 uni_tool/drivers/markdown.py 新增驱动实现 render/parse/can_handle/can_handle_response"
```

---

## 并行示例: 用户故事 3

```bash
# 一起启动用户故事 3 的实现:
任务: "在 uni_tool/middlewares/base.py 更新 deduplicate_middlewares 使用稳定 uid 覆盖逻辑"
任务: "在 uni_tool/core/execution.py 将 execute_tool_calls 改为 asyncio.gather 并保持结果顺序"
```

---

## 实施策略

### 仅 MVP(仅用户故事 1)

1. 完成阶段 1: 设置
2. 完成阶段 2: 基础(关键 - 阻塞所有故事)
3. 完成阶段 3: 用户故事 1
4. 独立测试用户故事 1
5. 如准备好则部署/演示

### 增量交付

1. 完成设置 + 基础 → 基础就绪
2. 添加用户故事 1 → 独立测试 → 部署/演示(MVP)
3. 添加用户故事 2 → 独立测试 → 部署/演示
4. 添加用户故事 3 → 独立测试 → 部署/演示
5. 每个故事在不破坏先前故事的情况下增加价值

