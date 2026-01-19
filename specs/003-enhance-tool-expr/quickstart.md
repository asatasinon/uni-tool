# ToolExpression 增强 快速入门

## 安装依赖

```bash
uv add lark
```

## DSL 过滤与诊断示例

```python
from uni_tool import universe
from uni_tool.core.expression_parser import ExpressionParser


@universe.tool(tags={"network"})
def ping(host: str) -> str:
    return f"pong:{host}"


@universe.tool(tags={"io", "deprecated"})
def legacy_io(path: str) -> str:
    return f"legacy:{path}"


def run_demo() -> None:
    parser = ExpressionParser()
    expr = parser.parse("(network | io) & ~deprecated")

    # 1) 直接使用表达式过滤
    tool_set = universe[expr]
    print([tool.name for tool in tool_set.tools])

    # 2) Universe 直接接收 DSL 字符串
    tool_set_from_dsl = universe["network | io"]
    print([tool.name for tool in tool_set_from_dsl.tools])

    # 3) 诊断某个工具为何被拒绝
    metadata = universe.get("legacy_io")
    if metadata is not None:
        trace = expr.diagnose(metadata)
        print(trace)

    # 4) 简化与字符串化
    simplified = expr.simplify()
    print(simplified.to_dsl())


if __name__ == "__main__":
    run_demo()
```

## DSL 语法速览

- `|`：OR
- `&`：AND
- `~`：NOT
- `()`：分组
- `name:tool_name`：工具名称精准匹配
- `prefix:tool_`：名称前缀匹配
- `^tool_`：等价于 `prefix:tool_`
- `` `tool_name` ``：等价于 `name:tool_name`
- `tags:(finance | ops)`：标签表达式（与直接标签等价）
