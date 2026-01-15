"""
工具过滤与视图示例 (Tool Filtering & Views)

展示如何使用 ToolExpression (Tag, Prefix, And, Or, Not) 来筛选工具集合，
并为不同的场景（或不同的 LLM）生成定制化的工具定义 (Schema)。

这在以下场景非常有用：
1. 权限控制：只给 LLM 暴露当前用户有权使用的工具。
2. 上下文缩减：根据任务类型（如"财务助手" vs "代码助手"）仅加载相关工具，节省 Token。
3. 动态视图：运行时动态组合工具集。
"""

import json

from uni_tool import Universe
from uni_tool.core.models import Prefix, Tag
from uni_tool.drivers.openai import OpenAIDriver

universe = Universe()
driver = OpenAIDriver()


# 1. 注册一系列工具，打上不同的 Tag
@universe.tool(name="finance_get_balance", tags={"finance", "read"})
def finance_get_balance(account_id: str):
    """Get account balance."""
    pass


@universe.tool(name="finance_transfer", tags={"finance", "write", "critical"})
def finance_transfer(to_account: str, amount: float):
    """Transfer money."""
    pass


@universe.tool(name="hr_get_employee", tags={"hr", "read"})
def hr_get_employee(emp_id: str):
    """Get employee details."""
    pass


@universe.tool(name="hr_update_salary", tags={"hr", "write", "admin"})
def hr_update_salary(emp_id: str, new_salary: float):
    """Update salary."""
    pass


@universe.tool(name="public_help", tags={"public", "common"})
def public_help():
    """Show help message."""
    pass


@universe.tool(name="system_status", tags={"system", "common"})
def system_status():
    """Check system status."""
    pass


def print_view(name: str, expression):
    """辅助函数：打印视图过滤出的工具名称"""
    # 使用 universe[expression] 获取 UniverseView
    view = universe[expression]

    # 获取过滤后的工具列表
    tools = view.get_tools()
    tool_names = sorted([t.name for t in tools])

    print(f"\n--- View: {name} ---")
    print(f"Expression: {expression}")
    print(f"Tools ({len(tools)}): {tool_names}")

    # 模拟生成 OpenAI Schema (仅打印数量)
    schema = view.render("openai")
    print(f"Generated Schema Count: {len(schema)}")


def main():
    print("=== 08 Tool Filtering & Views ===")

    # Case 1: 简单的 Tag 过滤
    # 场景：财务助手，只需要财务相关的工具
    print_view("Finance Bot", Tag("finance"))

    # Case 2: 组合逻辑 (AND)
    # 场景：只读权限的 HR 助手
    # 逻辑：必须是 HR 工具 且 必须有 read 标签
    print_view("HR Read-Only", Tag("hr") & Tag("read"))

    # Case 3: 组合逻辑 (OR)
    # 场景：通用助手，可以使用公共工具或系统工具
    print_view("General Helper", Tag("public") | Tag("system"))

    # Case 4: 组合逻辑 (NOT)
    # 场景：普通用户，不能看到 admin 工具
    # 逻辑：所有工具 排除 admin 标签
    # 注意：UniverseView 目前需要显式的包含逻辑，单纯的 Not 可能需要配合全集使用
    # 这里演示：(Finance OR HR) AND NOT Admin
    complex_expr = (Tag("finance") | Tag("hr")) & ~Tag("admin")
    print_view("Non-Admin Business Tools", complex_expr)

    # Case 5: 基于前缀过滤
    # 场景：通过命名规范筛选
    print_view("Finance Namespace", Prefix("finance_"))

    # Case 6: 实际 Schema 生成演示
    print("\n--- Schema Generation Example (Finance) ---")
    view = universe[Tag("finance")]
    schema = view.render("openai")
    print(json.dumps(schema, indent=2))


if __name__ == "__main__":
    main()
