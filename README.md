# UniTools SDK

## 快速开始

本项目使用 [uv](https://github.com/astral-sh/uv) 进行极速包管理。

### 1. 安装 uv
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 初始化环境
```bash
# 创建虚拟环境并安装依赖
uv sync

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### 3. 常用命令
```bash
# 添加依赖
uv add <package_name>

# 运行脚本
uv run main.py

# 运行测试
uv run pytest
```

## 开发指南

详细开发准则请参考 `CLAUDE.md` 和 `.specify/memory/constitution.md`。

### 核心工作流

1.  **工具表达式开发 (Tool Expression)**:
    *   专注于 `uni_tool/core/expressions.py` 和相关逻辑。
    *   使用 `uv run pytest tests/unit/test_expression.py` 验证更改。

2.  **中间件开发 (Middleware)**:
    *   在 `uni_tool/middlewares/` 中实现新的中间件。
    *   确保遵循**纵深防御**和**上下文隔离**原则。
    *   使用 `uv run pytest tests/unit/test_middleware.py` 验证更改。

3.  **规范驱动开发**:
    *   使用 `/speckit` 系列命令进行功能开发。
