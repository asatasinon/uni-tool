---
description: 启动中间件(Middleware)开发工作流, 包含测试验证.
---

## 目的

指导开发者进行中间件 (`uni_tool/middlewares/`) 的开发、调试和测试，确保符合 "纵深防御" 和 "治理" 原则。

## 用户输入

```text
$ARGUMENTS
```

## 执行步骤

1.  **上下文加载**:
    - 读取 `uni_tool/middlewares/base.py` 以理解中间件基类和接口。
    - 读取 `uni_tool/middlewares/__init__.py` 查看现有中间件注册情况。
    - 读取 `tests/unit/test_middleware.py` 以理解中间件测试模式。

2.  **原则确认**:
    - **独立性**: 中间件应只关注横切关注点（如日志、审计、鉴权），不应包含业务逻辑。
    - **上下文隔离**: 检查是否正确处理了 `Context` 对象。

3.  **基准测试 (Pre-check)**:
    - 运行现有测试以确保基准环境正常:
      ```bash
      uv run pytest tests/unit/test_middleware.py
      ```

4.  **开发循环**:
    - **新建/修改**: 
      - 如果是新中间件，在 `uni_tool/middlewares/` 下创建新文件（例如 `my_middleware.py`），继承 `BaseMiddleware`。
      - 如果是修改，编辑现有文件。
    - **新增测试**: 在 `tests/unit/test_middleware.py` 中添加针对新中间件的测试类/方法。
    - **验证**: 运行测试命令验证更改:
      ```bash
      uv run pytest tests/unit/test_middleware.py
      ```

5.  **集成检查**:
    - 确保新中间件可以在 `Universe` 或 `Tool` 级别正确注册和配置。

6.  **提交建议**:
    - 完成后，建议提交信息，例如: `feat(middleware): add [name] middleware` 或 `refactor(middleware): update [name] logic`。
