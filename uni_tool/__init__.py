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
# Errors
from uni_tool.core.errors import (
    DuplicateToolError,
    MiddlewareError,
    MissingContextKeyError,
    ProtocolDetectionError,
    ToolExecutionError,
    ToolFilterDeniedError,
    ToolNotFoundError,
    UniToolError,
    UnsupportedResponseFormatError,
)

# Tool filters
from uni_tool.core.expressions import And, Not, Or, ToolExpression
from uni_tool.core.models import (
    MiddlewareObj,
    ModelProfile,
    NextHandler,
    ToolCall,
    ToolMetadata,
    ToolResult,
    ToolSet,
)

# Universe (core runtime)
from uni_tool.core.universe import Universe
from uni_tool.drivers.anthropic import AnthropicDriver

# Drivers
from uni_tool.drivers.base import BaseDriver
from uni_tool.drivers.deepseek import DeepSeekDriver
from uni_tool.drivers.gemini import GeminiDriver
from uni_tool.drivers.glm import GLMDriver
from uni_tool.drivers.markdown import MarkdownDriver
from uni_tool.drivers.openai import OpenAIDriver
from uni_tool.drivers.xml import XMLDriver
from uni_tool.filters import Prefix, Tag, ToolName
from uni_tool.middlewares.audit import AuditMiddleware, create_audit_middleware

# Middlewares
from uni_tool.middlewares.base import MiddlewareProtocol
from uni_tool.middlewares.logging import LoggingMiddleware, create_logging_middleware
from uni_tool.middlewares.monitor import MonitorMiddleware, create_monitor_middleware

# Dependency injection
from uni_tool.utils.injection import Injected

# Create and configure the global universe instance
universe = Universe()
universe.register_driver("openai", OpenAIDriver())
universe.register_driver("anthropic", AnthropicDriver())
universe.register_driver("gemini", GeminiDriver())
universe.register_driver("deepseek", DeepSeekDriver())
universe.register_driver("glm", GLMDriver())
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
    # Dependency injection
    "Injected",
    # Drivers
    "BaseDriver",
    "OpenAIDriver",
    "AnthropicDriver",
    "GeminiDriver",
    "DeepSeekDriver",
    "GLMDriver",
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

__version__ = "0.3.1"
