"""
Universe - The central singleton for tool registration and management.

This module implements the core registry pattern for UniTools SDK.
"""

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    TYPE_CHECKING,
    overload,
)

from uni_tool.core.models import (
    ToolMetadata,
    ToolCall,
    ToolResult,
    MiddlewareObj,
    ToolExpression,
)
from uni_tool.core.errors import (
    DuplicateToolError,
    ToolNotFoundError,
)

if TYPE_CHECKING:
    from uni_tool.drivers.base import BaseDriver


class UniverseView:
    """
    A filtered view of the Universe for a specific tool expression.

    This allows chaining operations like `universe[Tag("finance")].render("gpt-4o")`.
    """

    def __init__(self, universe: "Universe", expression: ToolExpression):
        self._universe = universe
        self._expression = expression

    def get_tools(self) -> List[ToolMetadata]:
        """Get all tools matching the expression."""
        return [
            meta
            for meta in self._universe._registry.values()
            if self._expression.matches(meta)
        ]

    def render(self, driver_or_model: str) -> Any:
        """Render the filtered tools using the specified driver."""
        driver = self._universe._get_driver(driver_or_model)
        return driver.render(self.get_tools())


class Universe:
    """
    The central singleton for tool registration and execution.

    Universe manages:
    - Tool registration via @tool and @bind decorators
    - Middleware registration via use() method
    - Tool filtering via ToolExpression
    - Execution dispatching with middleware pipeline
    """

    _instance: Optional["Universe"] = None
    _initialized: bool = False

    def __new__(cls) -> "Universe":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if Universe._initialized:
            return
        Universe._initialized = True

        # Tool registry: name -> ToolMetadata
        self._registry: Dict[str, ToolMetadata] = {}

        # Middleware storage
        self._global_middlewares: List[MiddlewareObj] = []
        self._scoped_middlewares: List[MiddlewareObj] = []

        # Driver registry
        self._drivers: Dict[str, "BaseDriver"] = {}

        # Default driver alias mappings (model -> driver name)
        self._driver_aliases: Dict[str, str] = {
            "gpt-4": "openai",
            "gpt-4o": "openai",
            "gpt-4o-mini": "openai",
            "gpt-3.5-turbo": "openai",
        }

    def register(self, metadata: ToolMetadata) -> None:
        """
        Register a tool with the Universe.

        Args:
            metadata: The tool metadata to register.

        Raises:
            DuplicateToolError: If a tool with the same name already exists.
        """
        if metadata.name in self._registry:
            raise DuplicateToolError(metadata.name)
        self._registry[metadata.name] = metadata

    def unregister(self, name: str) -> None:
        """
        Unregister a tool from the Universe.

        Args:
            name: The name of the tool to unregister.

        Raises:
            ToolNotFoundError: If the tool is not registered.
        """
        if name not in self._registry:
            raise ToolNotFoundError(name)
        del self._registry[name]

    def get(self, name: str) -> Optional[ToolMetadata]:
        """
        Get a tool's metadata by name.

        Args:
            name: The name of the tool.

        Returns:
            The tool metadata, or None if not found.
        """
        return self._registry.get(name)

    def get_all(self) -> List[ToolMetadata]:
        """
        Get all registered tools.

        Returns:
            A list of all tool metadata.
        """
        return list(self._registry.values())

    @property
    def tools(self) -> Dict[str, ToolMetadata]:
        """Get a copy of the tool registry."""
        return dict(self._registry)

    @property
    def tool_names(self) -> Set[str]:
        """Get the set of all registered tool names."""
        return set(self._registry.keys())

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._registry

    def __len__(self) -> int:
        """Get the number of registered tools."""
        return len(self._registry)

    @overload
    def __getitem__(self, key: str) -> ToolMetadata: ...

    @overload
    def __getitem__(self, key: ToolExpression) -> UniverseView: ...

    def __getitem__(self, key: str | ToolExpression) -> ToolMetadata | UniverseView:
        """
        Access tools by name or filter by expression.

        Args:
            key: Either a tool name (str) or a ToolExpression.

        Returns:
            ToolMetadata if key is a string, UniverseView if key is a ToolExpression.

        Raises:
            ToolNotFoundError: If key is a string and the tool is not found.
        """
        if isinstance(key, str):
            if key not in self._registry:
                raise ToolNotFoundError(key)
            return self._registry[key]
        elif isinstance(key, ToolExpression):
            return UniverseView(self, key)
        else:
            raise TypeError(f"Key must be str or ToolExpression, got {type(key)}")

    def use(
        self,
        middleware: Callable[[ToolCall, Any], Any],
        *,
        critical: bool = True,
        scope: Optional[ToolExpression] = None,
        uid: Optional[str] = None,
    ) -> None:
        """
        Register a middleware function.

        Args:
            middleware: The middleware function with signature `async (call, next) -> result`.
            critical: If True, middleware failure aborts the pipeline.
            scope: Optional ToolExpression to limit middleware scope.
            uid: Optional unique identifier for deduplication.
        """
        mw_obj = MiddlewareObj(
            func=middleware,
            critical=critical,
            scope=scope,
            uid=uid or "",
        )

        if scope is None:
            self._global_middlewares.append(mw_obj)
        else:
            self._scoped_middlewares.append(mw_obj)

    def register_driver(self, name: str, driver: "BaseDriver") -> None:
        """
        Register a protocol driver.

        Args:
            name: The driver name (e.g., "openai").
            driver: The driver instance.
        """
        self._drivers[name] = driver

    def _get_driver(self, driver_or_model: str) -> "BaseDriver":
        """
        Get a driver by name or model alias.

        Args:
            driver_or_model: Either a driver name or model name.

        Returns:
            The driver instance.

        Raises:
            ValueError: If no driver is found.
        """
        # Direct driver lookup
        if driver_or_model in self._drivers:
            return self._drivers[driver_or_model]

        # Alias lookup
        driver_name = self._driver_aliases.get(driver_or_model)
        if driver_name and driver_name in self._drivers:
            return self._drivers[driver_name]

        raise ValueError(f"No driver found for '{driver_or_model}'")

    def render(self, driver_or_model: str) -> Any:
        """
        Render all tools using the specified driver.

        Args:
            driver_or_model: Either a driver name or model name.

        Returns:
            The rendered tool schema (format depends on driver).
        """
        driver = self._get_driver(driver_or_model)
        return driver.render(self.get_all())

    async def dispatch(
        self,
        response: Any,
        *,
        context: Optional[Dict[str, Any]] = None,
        driver_or_model: str = "openai",
    ) -> List[ToolResult]:
        """
        Parse and execute tool calls from an LLM response.

        Args:
            response: The LLM response containing tool calls.
            context: Context data for dependency injection.
            driver_or_model: The driver to use for parsing.

        Returns:
            A list of ToolResult objects.
        """
        from uni_tool.core.execution import execute_tool_calls

        driver = self._get_driver(driver_or_model)
        calls = driver.parse(response)

        # Enrich calls with context
        if context:
            for call in calls:
                call.context.update(context)

        return await execute_tool_calls(self, calls)

    def tool(
        self,
        *,
        name: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        middlewares: Optional[List[MiddlewareObj]] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator to register a function as a tool.

        Args:
            name: Optional custom name (defaults to function name).
            tags: Optional tags for filtering.
            middlewares: Optional tool-level middlewares.

        Returns:
            A decorator function.
        """
        from uni_tool.decorators.tool import create_tool_decorator

        return create_tool_decorator(
            self,
            name=name,
            tags=tags,
            middlewares=middlewares,
        )

    def bind(
        self,
        *,
        prefix: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> Callable[[type], type]:
        """
        Decorator to register all methods of a class as tools.

        Args:
            prefix: Optional prefix for tool names.
            tags: Optional tags applied to all methods.

        Returns:
            A class decorator.
        """
        from uni_tool.decorators.bind import create_bind_decorator

        return create_bind_decorator(
            self,
            prefix=prefix,
            tags=tags,
        )

    def _reset(self) -> None:
        """
        Reset the Universe state. FOR TESTING ONLY.

        This method clears all registered tools and middlewares.
        """
        self._registry.clear()
        self._global_middlewares.clear()
        self._scoped_middlewares.clear()
        self._drivers.clear()
