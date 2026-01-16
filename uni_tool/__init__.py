"""
UniTools SDK - A unified tool registration and execution framework for LLM agents.

This module exports the core components of the UniTools SDK.

Quick Start:
    from uni_tool import universe, Injected, Tag
    from typing import Annotated

    @universe.tool(tags={"finance"})
    async def get_balance(
        currency: str,
        user_id: Annotated[str, Injected("uid")]
    ):
        '''Get user balance.'''
        return {"amount": 100.0, "currency": currency}

    # Register middleware
    universe.use(my_middleware)

    # Dispatch tool calls
    results = await universe.dispatch(response, context={"uid": "user_001"})
"""

# Core models
from uni_tool.core.models import (
    ToolMetadata,
    ToolCall,
    ToolResult,
    MiddlewareObj,
    ToolSet,
    ModelProfile,
)

# Tool filters
from uni_tool.core.filters import (
    ToolExpression,
    Tag,
    Prefix,
    And,
    Or,
    Not,
    ToolName,
    ToolFilter,
)

# Errors
from uni_tool.core.errors import (
    UniToolError,
    DuplicateToolError,
    MissingContextKeyError,
    ToolNotFoundError,
    ToolExecutionError,
    UnsupportedResponseFormatError,
    MiddlewareError,
    ToolFilterDeniedError,
    ProtocolDetectionError,
)

# Universe (core runtime)
from uni_tool.core.universe import Universe

# Dependency injection
from uni_tool.utils.injection import Injected

# Drivers
from uni_tool.drivers.base import BaseDriver
from uni_tool.drivers.openai import OpenAIDriver
from uni_tool.drivers.anthropic import AnthropicDriver
from uni_tool.drivers.xml import XMLDriver
from uni_tool.drivers.markdown import MarkdownDriver

# Middlewares
from uni_tool.middlewares.base import MiddlewareProtocol
from uni_tool.core.models import NextHandler
from uni_tool.middlewares.audit import AuditMiddleware, create_audit_middleware
from uni_tool.middlewares.monitor import MonitorMiddleware, create_monitor_middleware
from uni_tool.middlewares.logging import LoggingMiddleware, create_logging_middleware


# Create and configure the global universe instance
universe = Universe()
universe.register_driver("openai", OpenAIDriver())
universe.register_driver("anthropic", AnthropicDriver())
universe.register_driver("xml", XMLDriver())
universe.register_driver("markdown", MarkdownDriver())


__all__ = [
    # Global instance
    "universe",
    # Core classes
    "Universe",
    "ToolSet",
    "ModelProfile",
    # Models
    "ToolMetadata",
    "ToolCall",
    "ToolResult",
    "MiddlewareObj",
    # Expressions
    "ToolExpression",
    "Tag",
    "Prefix",
    "And",
    "Or",
    "Not",
    "ToolName",
    "ToolFilter",
    # Dependency injection
    "Injected",
    # Drivers
    "BaseDriver",
    "OpenAIDriver",
    "AnthropicDriver",
    "XMLDriver",
    "MarkdownDriver",
    # Middlewares
    "MiddlewareProtocol",
    "NextHandler",
    "AuditMiddleware",
    "MonitorMiddleware",
    "LoggingMiddleware",
    "create_audit_middleware",
    "create_monitor_middleware",
    "create_logging_middleware",
    # Errors
    "UniToolError",
    "DuplicateToolError",
    "MissingContextKeyError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "UnsupportedResponseFormatError",
    "MiddlewareError",
    "ToolFilterDeniedError",
    "ProtocolDetectionError",
]

__version__ = "0.1.0"
