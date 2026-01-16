"""
UniTools SDK - 类绑定示例

展示如何使用 @bind 装饰器批量注册类的方法为工具：
- 自动注册公共方法
- 添加前缀避免命名冲突
- 统一应用标签
- 排除特定方法
"""

import asyncio
import json
from typing import Annotated, Optional

from uni_tool import universe, Injected, Tag


# =============================================================================
# 1. 基础类绑定
# =============================================================================


@universe.bind(prefix="math_", tags={"math", "utility"})
class MathService:
    """Mathematical operations service."""

    def add(self, a: float, b: float) -> float:
        """Add two numbers.

        Args:
            a: First number.
            b: Second number.
        """
        return a + b

    def multiply(self, x: float, y: float) -> float:
        """Multiply two numbers.

        Args:
            x: First factor.
            y: Second factor.
        """
        return x * y

    def divide(self, dividend: float, divisor: float) -> float:
        """Divide two numbers.

        Args:
            dividend: Number to be divided.
            divisor: Number to divide by.
        """
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return dividend / divisor

    def _internal_helper(self) -> None:
        """Private method - will NOT be registered."""
        pass


# =============================================================================
# 2. 带上下文注入的类绑定
# =============================================================================


@universe.bind(prefix="user_", tags={"user", "api"})
class UserService:
    """User management service with context injection."""

    def get_profile(
        self,
        user_id: Annotated[str, Injected("current_user_id")],
    ) -> dict:
        """Get current user's profile.

        Note: user_id is injected from context, not visible to LLM.
        """
        # 模拟数据
        profiles = {
            "u001": {"name": "Alice", "email": "alice@example.com"},
            "u002": {"name": "Bob", "email": "bob@example.com"},
        }
        return profiles.get(user_id, {"error": "User not found"})

    def update_settings(
        self,
        theme: str,
        language: str = "en",
        user_id: Annotated[str, Injected("current_user_id")] = None,
    ) -> dict:
        """Update user settings.

        Args:
            theme: UI theme (light/dark).
            language: Language preference.
        """
        return {
            "user_id": user_id,
            "settings": {"theme": theme, "language": language},
            "status": "updated",
        }


# =============================================================================
# 3. 排除特定方法
# =============================================================================


@universe.bind(
    prefix="order_",
    tags={"order", "ecommerce"},
    exclude=["internal_validate", "deprecated_method"],
)
class OrderService:
    """Order management with method exclusion."""

    def create(self, product_id: str, quantity: int = 1) -> dict:
        """Create a new order.

        Args:
            product_id: Product identifier.
            quantity: Number of items.
        """
        return {
            "order_id": f"ORD_{product_id}_{quantity}",
            "status": "created",
        }

    def get_status(self, order_id: str) -> dict:
        """Get order status.

        Args:
            order_id: Order identifier.
        """
        return {"order_id": order_id, "status": "processing"}

    def internal_validate(self, order: dict) -> bool:
        """Internal validation - excluded from registration."""
        return True

    def deprecated_method(self) -> None:
        """Deprecated method - excluded from registration."""
        pass


# =============================================================================
# 4. 异步方法支持
# =============================================================================


@universe.bind(prefix="search_", tags={"search", "async"})
class SearchService:
    """Async search service."""

    async def products(
        self,
        query: str,
        limit: int = 10,
    ) -> list:
        """Search for products.

        Args:
            query: Search query.
            limit: Maximum results.
        """
        await asyncio.sleep(0.01)  # 模拟异步操作
        return [
            {"id": f"prod_{i}", "name": f"Product matching '{query}'", "score": 0.9 - i * 0.1}
            for i in range(min(limit, 5))
        ]

    async def users(
        self,
        name: str,
        department: Optional[str] = None,
    ) -> list:
        """Search for users.

        Args:
            name: Name to search.
            department: Filter by department.
        """
        await asyncio.sleep(0.01)
        results = [{"id": "u001", "name": name, "department": "Engineering"}]
        if department:
            results = [r for r in results if r["department"] == department]
        return results


# =============================================================================
# 5. 主程序
# =============================================================================


async def main():
    print("=" * 60)
    print("UniTools SDK - Class Binding Demo")
    print("=" * 60)

    # --- 查看注册的工具 ---
    print("\n[1] Registered tools by prefix:")

    prefixes = {"math_", "user_", "order_", "search_"}
    for prefix in prefixes:
        tools = [name for name in universe.tool_names if name.startswith(prefix)]
        print(f"  {prefix}*: {tools}")

    # --- 验证排除的方法未被注册 ---
    print("\n[2] Excluded methods check:")
    excluded = ["order_internal_validate", "order_deprecated_method", "math__internal_helper"]
    for name in excluded:
        status = "NOT registered" if name not in universe else "REGISTERED (unexpected!)"
        print(f"  {name}: {status}")

    # --- 执行工具调用 ---
    print("\n[3] Executing bound methods:")

    response = {
        "tool_calls": [
            # MathService
            {
                "id": "call_math",
                "type": "function",
                "function": {
                    "name": "math_add",
                    "arguments": json.dumps({"a": 10, "b": 20}),
                },
            },
            # UserService (with context injection)
            {
                "id": "call_user",
                "type": "function",
                "function": {
                    "name": "user_get_profile",
                    "arguments": "{}",  # user_id 从 context 注入
                },
            },
            # OrderService
            {
                "id": "call_order",
                "type": "function",
                "function": {
                    "name": "order_create",
                    "arguments": json.dumps({"product_id": "SKU_001", "quantity": 3}),
                },
            },
            # SearchService (async)
            {
                "id": "call_search",
                "type": "function",
                "function": {
                    "name": "search_products",
                    "arguments": json.dumps({"query": "laptop", "limit": 3}),
                },
            },
        ]
    }

    # 执行时注入 user context
    results = await universe.dispatch(
        response,
        context={"current_user_id": "u001"},
    )

    for result in results:
        print(f"\n  [{result.id}]")
        if result.is_success:
            print(f"    Result: {result.result}")
        else:
            print(f"    Error: {result.error}")

    # --- 按标签过滤 ---
    print("\n[4] Filter tools by tag:")

    math_tools = universe[Tag("math")].tools
    print(f"  Tag('math'): {[t.name for t in math_tools]}")

    async_tools = universe[Tag("async")].tools
    print(f"  Tag('async'): {[t.name for t in async_tools]}")

    # --- 渲染特定标签的 schema ---
    print("\n[5] Schema for 'ecommerce' tools:")
    schema = universe[Tag("ecommerce")].render("openai")
    for tool in schema:
        print(f"  - {tool['function']['name']}")
        params = tool["function"]["parameters"]["properties"]
        print(f"    params: {list(params.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
