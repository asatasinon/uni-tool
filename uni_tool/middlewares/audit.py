"""
Audit middleware for UniTools SDK.

Records tool invocations, inputs, outputs, and timing information.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime

from uni_tool.core.models import ToolCall, MiddlewareObj

logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    """
    A single audit log entry.

    Attributes:
        tool_name: Name of the invoked tool.
        call_id: The tool call ID.
        arguments: The arguments passed to the tool (sanitized).
        result: The result of the execution (if successful).
        error: The error message (if failed).
        elapsed_ms: Execution time in milliseconds.
        timestamp: When the call was made.
        context_keys: Keys present in the context (not values for privacy).
    """

    tool_name: str
    call_id: str
    arguments: dict
    result: Any = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    context_keys: list[str] = field(default_factory=list)


class AuditMiddleware:
    """
    Middleware that audits tool invocations.

    Usage:
        audit = AuditMiddleware()
        universe.use(audit, critical=False)

        # Later, access audit records
        for record in audit.records:
            print(f"{record.tool_name}: {record.elapsed_ms}ms")
    """

    def __init__(
        self,
        *,
        max_records: int = 1000,
        log_level: int = logging.INFO,
        sanitize_args: Optional[Callable[[dict], dict]] = None,
    ):
        """
        Initialize the audit middleware.

        Args:
            max_records: Maximum number of records to keep (FIFO).
            log_level: Logging level for audit messages.
            sanitize_args: Optional function to sanitize arguments before logging.
        """
        self.max_records = max_records
        self.log_level = log_level
        self.sanitize_args = sanitize_args or (lambda x: x)
        self._records: list[AuditRecord] = []

    @property
    def records(self) -> list[AuditRecord]:
        """Get all audit records."""
        return list(self._records)

    def clear(self) -> None:
        """Clear all audit records."""
        self._records.clear()

    async def __call__(self, call: ToolCall, next_handler: Any) -> Any:
        """
        Process the call and record audit information.

        Args:
            call: The tool call.
            next_handler: The next handler in the pipeline.

        Returns:
            The result from the next handler.
        """
        start_time = time.perf_counter()
        error_msg: Optional[str] = None
        result: Any = None

        try:
            result = await next_handler(call)
            return result
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            elapsed = (time.perf_counter() - start_time) * 1000

            # Create audit record
            record = AuditRecord(
                tool_name=call.name,
                call_id=call.id,
                arguments=self.sanitize_args(dict(call.arguments)),
                result=result if error_msg is None else None,
                error=error_msg,
                elapsed_ms=round(elapsed, 2),
                context_keys=list(call.context.keys()),
            )

            # Store record (with FIFO eviction)
            self._records.append(record)
            if len(self._records) > self.max_records:
                self._records.pop(0)

            # Log the audit entry
            if error_msg:
                logger.log(
                    self.log_level,
                    f"[AUDIT] {call.name} (id={call.id}) FAILED in {elapsed:.2f}ms: {error_msg}",
                )
            else:
                logger.log(
                    self.log_level,
                    f"[AUDIT] {call.name} (id={call.id}) OK in {elapsed:.2f}ms",
                )


def create_audit_middleware(
    *,
    max_records: int = 1000,
    critical: bool = False,
    uid: str = "audit",
) -> tuple[AuditMiddleware, MiddlewareObj]:
    """
    Factory function to create an audit middleware and its wrapper.

    Args:
        max_records: Maximum audit records to keep.
        critical: Whether middleware failure should abort the pipeline.
        uid: Unique identifier for deduplication.

    Returns:
        A tuple of (AuditMiddleware instance, MiddlewareObj for registration).
    """
    audit = AuditMiddleware(max_records=max_records)
    mw_obj = MiddlewareObj(
        func=audit,
        critical=critical,
        scope=None,
        uid=uid,
    )
    return audit, mw_obj
