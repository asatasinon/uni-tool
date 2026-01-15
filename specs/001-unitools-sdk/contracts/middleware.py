from typing import Protocol, Callable, Awaitable, Any
from .driver import ToolCall

# NextHandler is an async function that takes a ToolCall and returns Any (Result)
NextHandler = Callable[[ToolCall], Awaitable[Any]]


class MiddlewareProtocol(Protocol):
    """
    Protocol for Middleware functions.
    """

    async def __call__(self, call: ToolCall, next_handler: NextHandler) -> Any:
        """
        Process the call, optionally invoking next_handler.

        Args:
            call: The current tool call object (with context).
            next_handler: The next function in the pipeline.

        Returns:
            The result of the execution.
        """
        ...
