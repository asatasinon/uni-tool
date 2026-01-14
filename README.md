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
