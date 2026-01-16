"""
UniTools SDK - 真实世界场景: 智能客服机器人

展示一个接近生产环境的完整示例：
- 多个业务域工具（订单、产品、用户）
- 完整的中间件链（日志、审计、限流）
- 上下文注入（用户身份）
- 权限控制（基于角色的工具过滤）
- 错误处理和结果格式化
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Annotated, Optional

from uni_tool import (
    universe,
    Injected,
    Tag,
    AuditMiddleware,
    MonitorMiddleware,
    ToolCall,
)

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# 1. 中间件设置
# =============================================================================

# 审计中间件
audit = AuditMiddleware(max_records=1000)
universe.use(audit, critical=False)

# 监控中间件
monitor = MonitorMiddleware()
universe.use(monitor, critical=False)


# 自定义：请求日志中间件
async def request_logger(call: ToolCall, next_handler) -> any:
    """记录每个工具调用的请求和响应。"""
    start = datetime.now()
    logger.info(f"[{start.strftime('%H:%M:%S')}] -> {call.name}({call.arguments})")

    try:
        result = await next_handler(call)
        logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] <- {call.name}: OK")
        return result
    except Exception as e:
        logger.error(f"[{datetime.now().strftime('%H:%M:%S')}] <- {call.name}: ERROR {e}")
        raise


universe.use(request_logger, critical=False)


# =============================================================================
# 2. 模拟数据库
# =============================================================================

MOCK_DB = {
    "users": {
        "u001": {"name": "张三", "email": "zhang@example.com", "role": "customer", "vip": True},
        "u002": {"name": "李四", "email": "li@example.com", "role": "customer", "vip": False},
        "admin": {"name": "管理员", "email": "admin@example.com", "role": "admin", "vip": True},
    },
    "orders": {
        "ORD001": {"user_id": "u001", "product": "iPhone 15", "status": "shipped", "total": 6999},
        "ORD002": {"user_id": "u001", "product": "AirPods Pro", "status": "delivered", "total": 1999},
        "ORD003": {"user_id": "u002", "product": "MacBook Pro", "status": "processing", "total": 14999},
    },
    "products": {
        "P001": {"name": "iPhone 15", "price": 6999, "stock": 100, "category": "phone"},
        "P002": {"name": "AirPods Pro", "price": 1999, "stock": 500, "category": "accessory"},
        "P003": {"name": "MacBook Pro", "price": 14999, "stock": 50, "category": "laptop"},
    },
}


# =============================================================================
# 3. 业务工具 - 订单服务
# =============================================================================


@universe.tool(tags={"order", "query", "customer"})
async def get_my_orders(
    status: Optional[str] = None,
    user_id: Annotated[str, Injected("current_user_id")] = None,
) -> dict:
    """查询当前用户的订单列表。

    Args:
        status: 订单状态筛选 (processing/shipped/delivered)
    """
    orders = [{**order, "order_id": oid} for oid, order in MOCK_DB["orders"].items() if order["user_id"] == user_id]

    if status:
        orders = [o for o in orders if o["status"] == status]

    return {
        "count": len(orders),
        "orders": orders,
    }


@universe.tool(tags={"order", "query", "customer"})
async def get_order_detail(
    order_id: str,
    user_id: Annotated[str, Injected("current_user_id")] = None,
) -> dict:
    """查询订单详情。

    Args:
        order_id: 订单号
    """
    order = MOCK_DB["orders"].get(order_id)

    if not order:
        return {"error": f"订单 {order_id} 不存在"}

    if order["user_id"] != user_id:
        return {"error": "无权查看此订单"}

    return {
        "order_id": order_id,
        **order,
        "estimated_delivery": "2024-01-20" if order["status"] != "delivered" else None,
    }


@universe.tool(tags={"order", "action", "customer"})
async def cancel_order(
    order_id: str,
    reason: str,
    user_id: Annotated[str, Injected("current_user_id")] = None,
) -> dict:
    """取消订单。

    Args:
        order_id: 订单号
        reason: 取消原因
    """
    order = MOCK_DB["orders"].get(order_id)

    if not order:
        return {"success": False, "message": f"订单 {order_id} 不存在"}

    if order["user_id"] != user_id:
        return {"success": False, "message": "无权操作此订单"}

    if order["status"] == "delivered":
        return {"success": False, "message": "已送达订单无法取消"}

    return {
        "success": True,
        "message": f"订单 {order_id} 已取消",
        "refund_amount": order["total"],
        "refund_eta": "3-5个工作日",
    }


# =============================================================================
# 4. 业务工具 - 产品服务
# =============================================================================


@universe.tool(tags={"product", "query", "public"})
async def search_products(
    keyword: str,
    category: Optional[str] = None,
    max_price: Optional[float] = None,
) -> dict:
    """搜索产品。

    Args:
        keyword: 搜索关键词
        category: 产品类别 (phone/laptop/accessory)
        max_price: 最高价格
    """
    results = []

    for pid, product in MOCK_DB["products"].items():
        if keyword.lower() not in product["name"].lower():
            continue
        if category and product["category"] != category:
            continue
        if max_price and product["price"] > max_price:
            continue
        results.append({"product_id": pid, **product})

    return {
        "count": len(results),
        "products": results,
    }


@universe.tool(tags={"product", "query", "public"})
async def get_product_info(product_id: str) -> dict:
    """获取产品详情。

    Args:
        product_id: 产品ID
    """
    product = MOCK_DB["products"].get(product_id)

    if not product:
        return {"error": f"产品 {product_id} 不存在"}

    return {
        "product_id": product_id,
        **product,
        "in_stock": product["stock"] > 0,
    }


# =============================================================================
# 5. 业务工具 - 用户服务
# =============================================================================


@universe.tool(tags={"user", "query", "customer"})
async def get_my_profile(
    user_id: Annotated[str, Injected("current_user_id")] = None,
) -> dict:
    """获取当前用户信息。"""
    user = MOCK_DB["users"].get(user_id)

    if not user:
        return {"error": "用户不存在"}

    return {
        "user_id": user_id,
        "name": user["name"],
        "email": user["email"],
        "vip_status": "VIP会员" if user["vip"] else "普通会员",
    }


@universe.tool(tags={"user", "action", "customer"})
async def update_email(
    new_email: str,
    user_id: Annotated[str, Injected("current_user_id")] = None,
) -> dict:
    """更新邮箱地址。

    Args:
        new_email: 新邮箱地址
    """
    if "@" not in new_email:
        return {"success": False, "message": "邮箱格式不正确"}

    return {
        "success": True,
        "message": f"邮箱已更新为 {new_email}",
        "verification_sent": True,
    }


# =============================================================================
# 6. 管理员工具
# =============================================================================


@universe.tool(tags={"admin", "query"})
async def get_all_orders(
    status: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """[管理员] 查询所有订单。

    Args:
        status: 订单状态筛选
        limit: 返回数量限制
    """
    orders = [{"order_id": oid, **order} for oid, order in list(MOCK_DB["orders"].items())[:limit]]

    if status:
        orders = [o for o in orders if o["status"] == status]

    return {"count": len(orders), "orders": orders}


@universe.tool(tags={"admin", "action"})
async def update_order_status(
    order_id: str,
    new_status: str,
) -> dict:
    """[管理员] 更新订单状态。

    Args:
        order_id: 订单号
        new_status: 新状态 (processing/shipped/delivered)
    """
    if order_id not in MOCK_DB["orders"]:
        return {"success": False, "message": "订单不存在"}

    return {
        "success": True,
        "message": f"订单 {order_id} 状态已更新为 {new_status}",
    }


# =============================================================================
# 7. 聊天机器人模拟器
# =============================================================================


class ChatBot:
    """智能客服机器人模拟器。"""

    def __init__(self, user_id: str, role: str = "customer"):
        self.user_id = user_id
        self.role = role
        self.context = {
            "current_user_id": user_id,
        }

        # 根据角色设置工具过滤器
        if role == "admin":
            self.tool_filter = None  # 管理员可以使用所有工具
        else:
            self.tool_filter = ~Tag("admin")  # 普通用户不能使用管理员工具

    async def handle_tool_calls(self, llm_response: dict) -> list:
        """处理 LLM 返回的工具调用。"""
        results = await universe.dispatch(
            llm_response,
            context=self.context,
            tool_filter=self.tool_filter,
        )
        return results

    def format_results(self, results: list) -> str:
        """格式化结果供用户阅读。"""
        output = []
        for r in results:
            if r.is_success:
                output.append(f"✅ {json.dumps(r.result, ensure_ascii=False, indent=2)}")
            else:
                output.append(f"❌ 错误: {r.error}")
        return "\n".join(output)


# =============================================================================
# 8. 主程序
# =============================================================================


async def main():
    print("=" * 60)
    print("智能客服机器人 Demo")
    print("=" * 60)

    # =========================================================================
    # 场景 1: 普通用户查询订单
    # =========================================================================
    print("\n" + "-" * 60)
    print("场景 1: 用户张三查询自己的订单")
    print("-" * 60)

    bot_customer = ChatBot(user_id="u001", role="customer")

    # 模拟 LLM 决定调用的工具
    llm_response_1 = {
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "get_my_profile",
                    "arguments": "{}",
                },
            },
            {
                "id": "call_2",
                "type": "function",
                "function": {
                    "name": "get_my_orders",
                    "arguments": "{}",
                },
            },
        ]
    }

    results = await bot_customer.handle_tool_calls(llm_response_1)
    print(bot_customer.format_results(results))

    # =========================================================================
    # 场景 2: 用户尝试访问管理员功能（应被拒绝）
    # =========================================================================
    print("\n" + "-" * 60)
    print("场景 2: 普通用户尝试访问管理员功能")
    print("-" * 60)

    llm_response_2 = {
        "tool_calls": [
            {
                "id": "call_admin",
                "type": "function",
                "function": {
                    "name": "get_all_orders",
                    "arguments": "{}",
                },
            },
        ]
    }

    results = await bot_customer.handle_tool_calls(llm_response_2)
    print(bot_customer.format_results(results))

    # =========================================================================
    # 场景 3: 管理员操作
    # =========================================================================
    print("\n" + "-" * 60)
    print("场景 3: 管理员查询并更新订单")
    print("-" * 60)

    bot_admin = ChatBot(user_id="admin", role="admin")

    llm_response_3 = {
        "tool_calls": [
            {
                "id": "call_query",
                "type": "function",
                "function": {
                    "name": "get_all_orders",
                    "arguments": json.dumps({"status": "processing"}),
                },
            },
            {
                "id": "call_update",
                "type": "function",
                "function": {
                    "name": "update_order_status",
                    "arguments": json.dumps({"order_id": "ORD003", "new_status": "shipped"}),
                },
            },
        ]
    }

    results = await bot_admin.handle_tool_calls(llm_response_3)
    print(bot_admin.format_results(results))

    # =========================================================================
    # 场景 4: 产品搜索（公开功能）
    # =========================================================================
    print("\n" + "-" * 60)
    print("场景 4: 产品搜索")
    print("-" * 60)

    llm_response_4 = {
        "tool_calls": [
            {
                "id": "call_search",
                "type": "function",
                "function": {
                    "name": "search_products",
                    "arguments": json.dumps({"keyword": "Pro", "max_price": 10000}),
                },
            },
        ]
    }

    results = await bot_customer.handle_tool_calls(llm_response_4)
    print(bot_customer.format_results(results))

    # =========================================================================
    # 统计信息
    # =========================================================================
    print("\n" + "=" * 60)
    print("运行统计")
    print("=" * 60)

    print("\n[审计记录]")
    for record in audit.records[-5:]:
        status = "✓" if record.error is None else "✗"
        print(f"  {status} {record.tool_name}: {record.elapsed_ms:.1f}ms")

    print("\n[性能指标]")
    metrics = monitor.export()
    for name, m in metrics.items():
        print(f"  {name}: 调用{m['call_count']}次, 成功率{m['success_rate']:.0%}, 平均{m['avg_duration_ms']:.1f}ms")


if __name__ == "__main__":
    asyncio.run(main())
