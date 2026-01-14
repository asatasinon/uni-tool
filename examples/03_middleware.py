"""
中间件示例 (Middleware)

展示如何使用内置的日志中间件，以及如何自定义中间件来拦截和处理工具调用。
"""

import asyncio
import logging
from typing import Any
from uni_tool import Universe
from uni_tool.core.models import ToolCall
from uni_tool.core.execution import execute_tool_calls
from uni_tool.middlewares.logging import create_logging_middleware

# 配置 logging 输出
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("examples")

universe = Universe()


# 1. 定义自定义中间件
# 中间件是一个异步可调用对象，接收 ToolCall 和 next_handler
class ValidationMiddleware:
    async def __call__(self, call: ToolCall, next_handler) -> Any:
        print(f"[Validation] Checking call {call.id}...")

        # 示例：简单的校验逻辑
        if "forbidden" in call.arguments.values():
            raise ValueError("Forbidden value detected!")

        # 继续执行下一个处理程序
        result = await next_handler(call)

        print(f"[Validation] Call {call.id} finished.")
        return result


# 2. 注册中间件
# 注册自定义中间件
universe.use(ValidationMiddleware())

# 注册内置的日志中间件
# create_logging_middleware 返回 (middleware_instance, middleware_obj)
# 我们只需要 middleware_instance 传给 universe.use
log_mw, _ = create_logging_middleware(logger=logger)
universe.use(log_mw)


@universe.tool(name="echo")
def echo(msg: str) -> str:
    """Echo the message back."""
    return msg


async def main():
    print("=== 03 Middleware ===")

    # Case 1: 正常调用
    call1 = ToolCall(id="c1", name="echo", arguments={"msg": "Hello"})
    await execute_tool_calls(universe, [call1])

    print("-" * 20)

    # Case 2: 触发自定义校验错误
    call2 = ToolCall(id="c2", name="echo", arguments={"msg": "forbidden"})
    results = await execute_tool_calls(universe, [call2])

    if results[0].error:
        print(f"Blocked as expected: {results[0].error}")


if __name__ == "__main__":
    asyncio.run(main())
