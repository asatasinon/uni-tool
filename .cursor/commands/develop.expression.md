---
description: 启动工具表达式(Tool Expression)开发工作流, 包含测试验证.
---

## 目的

指导开发者进行工具表达式 (`uni_tool/core/expressions.py` 等) 的开发、调试和测试，确保符合核心执行逻辑。

## 用户输入

```text
$ARGUMENTS
```

## 执行步骤

1.  **上下文加载**:
    - 读取 `uni_tool/core/executions.py` 以理解当前的表达式解析和执行逻辑。
    - 读取 `tests/unit/test_expression.py` 以理解现有的测试用例覆盖范围。

2.  **基准测试 (Pre-check)**:
    - 运行现有测试以确保基准环境正常:
      ```bash
      uv run pytest tests/unit/test_expression.py
      ```
    - 如果基准测试失败，停止并修复错误。

3.  **开发循环**:
    - **修改/实现**: 根据用户需求修改 `uni_tool/core/expressions.py` 或相关文件。
    - **新增测试**: 在 `tests/unit/test_expression.py` 中添加针对新逻辑的测试用例。
    - **验证**: 运行测试命令验证更改:
      ```bash
      uv run pytest tests/unit/test_expression.py
      ```

4.  **原则检查**:
    - **安全性**: 确保表达式执行没有引入任意代码执行漏洞。
    - **类型安全**: 确保新的逻辑包含适当的类型提示。
    - **错误处理**: 确保异常被适当地捕获和转换（例如转换为 `ExecutionError`）。

5.  **提交建议**:
    - 完成后，建议提交信息，例如: `feat(core): enhance tool expression logic for [feature]`。
