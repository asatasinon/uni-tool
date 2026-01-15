"""
综合应用示例 (Full Workflow)

结合所有特性：Universe, Driver, Middleware, Injection.
模拟一个完整的数据处理流程。
"""

import asyncio
import json
import logging
from typing import Annotated, Dict, List

from uni_tool import Injected, Universe
from uni_tool.core.execution import execute_tool_calls
from uni_tool.drivers.openai import OpenAIDriver
from uni_tool.middlewares.logging import create_logging_middleware

# Setup
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
universe = Universe()
driver = OpenAIDriver()

# Add Middleware
log_mw, _ = create_logging_middleware()
universe.use(log_mw)


# Define Tools
@universe.tool(name="search_database")
def search_database(query: str, limit: int = 5, db_conn: Annotated[str, Injected("db_connection")] = None) -> List[str]:
    """
    Search the database for records.
    """
    print(f"  -> DB Search on '{db_conn}' for '{query}' limit={limit}")
    return [f"Record {i} matching {query}" for i in range(1, limit + 1)]


@universe.tool(name="send_email")
def send_email(
    recipient: str, subject: str, body: str, user_email: Annotated[str, Injected("current_user_email")]
) -> str:
    """
    Send an email.
    """
    print(f"  -> Sending email from {user_email} to {recipient}")
    return "Email sent successfully"


async def run_agent_loop(user_input: str, context: Dict):
    print(f"\n--- Processing User Input: '{user_input}' ---")

    # 1. Export tools for LLM
    tools_def = driver.render(list(universe.tools.values()))
    # (Send tools_def and user_input to LLM...)
    print("Generated Tools Schema:")
    print(json.dumps(tools_def, indent=2))

    # 2. Simulate LLM deciding to call tools based on input
    # 假设用户说 "查找关于 'project alpha' 的记录并发送给 boss@company.com"
    mock_llm_response = {
        "tool_calls": [
            {
                "id": "call_search",
                "type": "function",
                "function": {"name": "search_database", "arguments": '{"query": "project alpha", "limit": 2}'},
            },
            {
                "id": "call_email",
                "type": "function",
                "function": {
                    "name": "send_email",
                    "arguments": '{"recipient": "boss@company.com", "subject": "Project Alpha Results", "body": "See attached..."}',
                },
            },
        ]
    }

    # 3. Parse Calls
    calls = driver.parse(mock_llm_response)

    # 4. Inject Context (Prepare calls with context)
    # uni-tool 的 execute 方法会自动处理 context，我们只需要把 context 传进去
    # 或者，我们可以在调用 execute 之前手动将 context 附加到每个 call 对象上
    # 但标准的做法是在 parse 之后，或者 execute 之前的一层做这个附加
    for call in calls:
        call.context = context

    # 5. Execute
    results = await execute_tool_calls(universe, calls)

    # 6. Process Results
    for res in results:
        if res.error:
            print(f"❌ Error in {res.id}: {res.error}")
        else:
            print(f"✅ Success {res.id}: {res.result}")


async def main():
    # Context that comes from the application environment (e.g. web request)
    app_context = {"db_connection": "postgres://localhost:5432/mydb", "current_user_email": "alice@company.com"}

    await run_agent_loop("Find project alpha stuff", app_context)


if __name__ == "__main__":
    asyncio.run(main())
