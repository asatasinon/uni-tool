"""
Logging middleware for UniTools SDK.

Provides structured logging for tool invocations.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Optional

from uni_tool.core.models import ToolCall, MiddlewareObj


class LoggingMiddleware:
    """
    Middleware that provides structured logging for tool invocations.

    Logs include:
    - Tool name and call ID
    - Arguments (optionally sanitized)
    - Execution time
    - Success/failure status
    - Error details on failure

    Usage:
        logger_mw = LoggingMiddleware(logger=logging.getLogger("tools"))
        universe.use(logger_mw)
    """

    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
        level: int = logging.INFO,
        error_level: int = logging.ERROR,
        log_arguments: bool = True,
        log_result: bool = False,
        sanitize: Optional[Callable[[dict], dict]] = None,
    ):
        """
        Initialize the logging middleware.

        Args:
            logger: Logger instance to use. Defaults to module logger.
            level: Log level for successful invocations.
            error_level: Log level for failed invocations.
            log_arguments: Whether to log arguments.
            log_result: Whether to log results (careful with sensitive data).
            sanitize: Optional function to sanitize arguments/results.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.level = level
        self.error_level = error_level
        self.log_arguments = log_arguments
        self.log_result = log_result
        self.sanitize = sanitize or (lambda x: x)

    async def __call__(self, call: ToolCall, next_handler: Any) -> Any:
        """
        Process the call and log information.

        Args:
            call: The tool call.
            next_handler: The next handler in the pipeline.

        Returns:
            The result from the next handler.
        """
        start_time = time.perf_counter()

        # Build log context
        log_data = {
            "tool": call.name,
            "call_id": call.id,
        }

        if self.log_arguments:
            log_data["arguments"] = self.sanitize(dict(call.arguments))

        self.logger.log(
            self.level,
            f"Tool invocation started: {call.name}",
            extra={"tool_data": log_data},
        )

        try:
            result = await next_handler(call)
            duration_ms = (time.perf_counter() - start_time) * 1000

            success_data = {
                **log_data,
                "duration_ms": round(duration_ms, 2),
                "status": "success",
            }

            if self.log_result:
                success_data["result"] = self.sanitize({"result": result})

            self.logger.log(
                self.level,
                f"Tool invocation completed: {call.name} ({duration_ms:.2f}ms)",
                extra={"tool_data": success_data},
            )

            return result

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000

            error_data = {
                **log_data,
                "duration_ms": round(duration_ms, 2),
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

            self.logger.log(
                self.error_level,
                f"Tool invocation failed: {call.name} - {e}",
                extra={"tool_data": error_data},
                exc_info=True,
            )

            raise


def create_logging_middleware(
    *,
    logger: Optional[logging.Logger] = None,
    level: int = logging.INFO,
    critical: bool = False,
    uid: str = "logging",
) -> tuple[LoggingMiddleware, MiddlewareObj]:
    """
    Factory function to create a logging middleware and its wrapper.

    Args:
        logger: Logger instance to use.
        level: Log level for invocations.
        critical: Whether middleware failure should abort the pipeline.
        uid: Unique identifier for deduplication.

    Returns:
        A tuple of (LoggingMiddleware instance, MiddlewareObj for registration).
    """
    logging_mw = LoggingMiddleware(logger=logger, level=level)
    mw_obj = MiddlewareObj(
        func=logging_mw,
        critical=critical,
        scope=None,
        uid=uid,
    )
    return logging_mw, mw_obj
