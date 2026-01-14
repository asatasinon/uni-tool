"""
Monitor middleware for UniTools SDK.

Collects metrics about tool invocations for observability.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict

from uni_tool.core.models import ToolCall, MiddlewareObj


@dataclass
class ToolMetrics:
    """
    Metrics for a single tool.

    Attributes:
        call_count: Total number of invocations.
        success_count: Number of successful invocations.
        error_count: Number of failed invocations.
        total_duration_ms: Total execution time in milliseconds.
        min_duration_ms: Minimum execution time.
        max_duration_ms: Maximum execution time.
    """

    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    max_duration_ms: float = 0.0

    @property
    def avg_duration_ms(self) -> float:
        """Calculate average duration."""
        if self.call_count == 0:
            return 0.0
        return self.total_duration_ms / self.call_count

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 - 1.0)."""
        if self.call_count == 0:
            return 0.0
        return self.success_count / self.call_count

    def record(self, duration_ms: float, success: bool) -> None:
        """Record a single invocation."""
        self.call_count += 1
        self.total_duration_ms += duration_ms

        if success:
            self.success_count += 1
        else:
            self.error_count += 1

        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)


class MonitorMiddleware:
    """
    Middleware that collects metrics about tool invocations.

    Usage:
        monitor = MonitorMiddleware()
        universe.use(monitor)

        # Later, access metrics
        metrics = monitor.get_metrics("my_tool")
        print(f"Avg duration: {metrics.avg_duration_ms}ms")

        # Export all metrics
        all_metrics = monitor.export()
    """

    def __init__(
        self,
        *,
        on_record: Optional[Callable[[str, float, bool], None]] = None,
    ):
        """
        Initialize the monitor middleware.

        Args:
            on_record: Optional callback called on each invocation.
                       Signature: (tool_name, duration_ms, success) -> None
        """
        self._metrics: Dict[str, ToolMetrics] = defaultdict(ToolMetrics)
        self._on_record = on_record

    def get_metrics(self, tool_name: str) -> ToolMetrics:
        """Get metrics for a specific tool."""
        return self._metrics[tool_name]

    def export(self) -> Dict[str, Dict[str, Any]]:
        """
        Export all metrics as a dictionary.

        Returns:
            Dictionary mapping tool names to their metrics.
        """
        return {
            name: {
                "call_count": m.call_count,
                "success_count": m.success_count,
                "error_count": m.error_count,
                "avg_duration_ms": round(m.avg_duration_ms, 2),
                "min_duration_ms": round(m.min_duration_ms, 2) if m.min_duration_ms != float("inf") else 0.0,
                "max_duration_ms": round(m.max_duration_ms, 2),
                "success_rate": round(m.success_rate, 4),
            }
            for name, m in self._metrics.items()
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()

    async def __call__(self, call: ToolCall, next_handler: Any) -> Any:
        """
        Process the call and record metrics.

        Args:
            call: The tool call.
            next_handler: The next handler in the pipeline.

        Returns:
            The result from the next handler.
        """
        start_time = time.perf_counter()
        success = True

        try:
            result = await next_handler(call)
            return result
        except Exception:
            success = False
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record metrics
            self._metrics[call.name].record(duration_ms, success)

            # Call callback if provided
            if self._on_record:
                self._on_record(call.name, duration_ms, success)


def create_monitor_middleware(
    *,
    critical: bool = False,
    uid: str = "monitor",
    on_record: Optional[Callable[[str, float, bool], None]] = None,
) -> tuple[MonitorMiddleware, MiddlewareObj]:
    """
    Factory function to create a monitor middleware and its wrapper.

    Args:
        critical: Whether middleware failure should abort the pipeline.
        uid: Unique identifier for deduplication.
        on_record: Optional callback for each invocation.

    Returns:
        A tuple of (MonitorMiddleware instance, MiddlewareObj for registration).
    """
    monitor = MonitorMiddleware(on_record=on_record)
    mw_obj = MiddlewareObj(
        func=monitor,
        critical=critical,
        scope=None,
        uid=uid,
    )
    return monitor, mw_obj
