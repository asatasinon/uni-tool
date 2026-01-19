"""
Unified exceptions for UniTools SDK.

All custom exceptions inherit from UniToolError for consistent error handling.
"""


class UniToolError(Exception):
    """Base exception for all UniTools SDK errors."""

    pass


class DuplicateToolError(UniToolError):
    """Raised when attempting to register a tool with a name that already exists."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Tool '{name}' is already registered")


class MissingContextKeyError(UniToolError):
    """Raised when a required context key for dependency injection is missing."""

    def __init__(self, key: str, tool_name: str):
        self.key = key
        self.tool_name = tool_name
        super().__init__(f"Missing required context key '{key}' for tool '{tool_name}'")


class ToolNotFoundError(UniToolError):
    """Raised when attempting to dispatch a tool that is not registered."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Tool '{name}' is not registered")


class ToolExecutionError(UniToolError):
    """Raised when a tool execution fails."""

    def __init__(self, name: str, original_error: Exception):
        self.name = name
        self.original_error = original_error
        super().__init__(f"Tool '{name}' execution failed: {original_error}")


class UnsupportedResponseFormatError(UniToolError):
    """Raised when the LLM response format is not supported by the driver."""

    def __init__(self, driver: str, message: str):
        self.driver = driver
        super().__init__(f"Driver '{driver}' cannot parse response: {message}")


class MiddlewareError(UniToolError):
    """Raised when a middleware encounters an error."""

    def __init__(self, middleware_name: str, original_error: Exception):
        self.middleware_name = middleware_name
        self.original_error = original_error
        super().__init__(f"Middleware '{middleware_name}' failed: {original_error}")


class ToolFilterDeniedError(UniToolError):
    """Raised when a tool call is denied by the filter."""

    def __init__(self, tool_name: str, filter_expression: str):
        self.tool_name = tool_name
        self.filter_expression = filter_expression
        super().__init__(f"Tool '{tool_name}' denied by filter: {filter_expression}")


class ProtocolDetectionError(UniToolError):
    """Raised when automatic protocol detection fails."""

    def __init__(self, message: str = "Unable to detect response protocol"):
        super().__init__(message)


class ExpressionParseError(UniToolError):
    """
    Raised when DSL expression parsing fails.

    Provides detailed error information including position and context.
    """

    def __init__(
        self,
        message: str,
        *,
        line: int,
        column: int,
        context: str,
    ):
        self.message = message
        self.line = line
        self.column = column
        self.context = context
        super().__init__(f"{message} at line {line}, column {column}: {context}")
