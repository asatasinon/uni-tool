"""
Universe - The central singleton for tool registration and management.

This module implements the core registry pattern for UniTools SDK.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    overload,
)

from uni_tool.core.errors import (
    DuplicateToolError,
    ToolNotFoundError,
)
from uni_tool.core.expressions import ToolExpression
from uni_tool.core.models import (
    MiddlewareObj,
    ModelProfile,
    ToolCall,
    ToolMetadata,
    ToolResult,
    ToolSet,
)
from uni_tool.filters import Tag

if TYPE_CHECKING:
    from uni_tool.drivers.base import BaseDriver


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
            "claude-3-opus": "anthropic",
            "claude-3-sonnet": "anthropic",
            "claude-3-haiku": "anthropic",
            "claude-3.5-sonnet": "anthropic",
            "gemini-2.5-flash": "gemini",
            "gemini-3-flash-preview": "gemini",
            "deepseek-chat": "deepseek",
            "glm-4.5": "glm",
        }

        # Model capability profiles
        self._model_profiles: Dict[str, ModelProfile] = {
            "gpt-4": ModelProfile(name="gpt-4", capabilities={"FC_NATIVE"}),
            "gpt-4o": ModelProfile(name="gpt-4o", capabilities={"FC_NATIVE"}),
            "gpt-4o-mini": ModelProfile(name="gpt-4o-mini", capabilities={"FC_NATIVE"}),
            "gpt-3.5-turbo": ModelProfile(name="gpt-3.5-turbo", capabilities={"FC_NATIVE"}),
            "claude-3-opus": ModelProfile(name="claude-3-opus", capabilities={"FC_NATIVE", "XML_FALLBACK"}),
            "claude-3-sonnet": ModelProfile(name="claude-3-sonnet", capabilities={"FC_NATIVE", "XML_FALLBACK"}),
            "claude-3-haiku": ModelProfile(name="claude-3-haiku", capabilities={"FC_NATIVE", "XML_FALLBACK"}),
            "claude-3.5-sonnet": ModelProfile(name="claude-3.5-sonnet", capabilities={"FC_NATIVE", "XML_FALLBACK"}),
            "gemini-2.5-flash": ModelProfile(name="gemini-2.5-flash", capabilities={"FC_NATIVE"}),
            "gemini-3-flash-preview": ModelProfile(name="gemini-3-flash-preview", capabilities={"FC_NATIVE"}),
            "deepseek-chat": ModelProfile(name="deepseek-chat", capabilities={"FC_NATIVE"}),
            "glm-4.5": ModelProfile(name="glm-4.5", capabilities={"FC_NATIVE"}),
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
    def __getitem__(self, key: str) -> ToolSet: ...

    @overload
    def __getitem__(self, key: ToolExpression) -> ToolSet: ...

    def __getitem__(self, key: str | ToolExpression) -> ToolSet:
        """
        Filter tools by tag string or expression.

        Args:
            key: Either a tag string (str) or a ToolExpression.
                - str: Treated as Tag filter, returns ToolSet with matching tools
                - ToolExpression: Returns ToolSet with tools matching the expression

        Returns:
            ToolSet containing matching tools (may be empty).

        Note:
            Use get(name) for accessing a single tool by name.
        """
        if isinstance(key, str):
            # String is treated as Tag filter
            expression = Tag(key)
        elif isinstance(key, ToolExpression):
            expression = key
        else:
            raise TypeError(f"Key must be str or ToolExpression, got {type(key)}")

        # Filter tools by expression
        matching_tools = [meta for meta in self._registry.values() if expression.matches(meta)]

        return ToolSet(
            tools=matching_tools,
            drivers=self._drivers,
            expression=expression,
            model_profile_getter=self._get_model_profile,
            driver_selector=self._select_driver_for_profile,
        )

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

    def _get_model_profile(self, model_name: str) -> ModelProfile:
        """
        Get or create a ModelProfile for the given model name.

        Args:
            model_name: The model name.

        Returns:
            The ModelProfile for the model.
        """
        if model_name in self._model_profiles:
            return self._model_profiles[model_name]

        # Create a default profile for unknown models
        return ModelProfile(name=model_name, capabilities=set())

    def _select_driver_for_profile(self, profile: ModelProfile) -> Optional["BaseDriver"]:
        """
        Select the best driver for a given model profile using can_handle scoring.

        Args:
            profile: The model profile.

        Returns:
            The best matching driver, or None if no driver can handle it.
        """
        if not self._drivers:
            return None

        scored = [(driver, driver.can_handle(profile)) for driver in self._drivers.values()]
        best_driver, best_score = max(scored, key=lambda x: x[1])

        return best_driver if best_score > 0 else None

    def _select_driver_for_response(self, response: Any) -> Optional[tuple["BaseDriver", str]]:
        """
        Select the best driver for parsing a response using can_handle_response scoring.

        Args:
            response: The raw LLM response.

        Returns:
            A tuple of (driver, driver_name), or None if no driver can handle it.
        """
        if not self._drivers:
            return None

        scored = [(driver, name, driver.can_handle_response(response)) for name, driver in self._drivers.items()]
        best_driver, best_name, best_score = max(scored, key=lambda x: x[2])

        return (best_driver, best_name) if best_score > 0 else None

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
        driver_or_model: Optional[str] = None,
        tool_filter: Optional[ToolExpression] = None,
    ) -> List[ToolResult]:
        """
        Parse and execute tool calls from an LLM response.

        Args:
            response: The LLM response containing tool calls.
            context: Context data for dependency injection.
            driver_or_model: The driver to use for parsing. If None, auto-detect.
            tool_filter: Optional ToolExpression to filter allowed tool calls.
                Denied calls return ToolResult with error but do not abort dispatch.

        Returns:
            A list of ToolResult objects.
        """
        from uni_tool.core.execution import execute_tool_calls

        # Select driver: explicit > auto-detect > fallback
        driver: Optional["BaseDriver"] = None
        driver_name: Optional[str] = None

        if driver_or_model:
            # Explicit driver specified
            driver = self._get_driver(driver_or_model)
            driver_name = driver_or_model
        else:
            # Auto-detect based on response fingerprint
            detection_result = self._select_driver_for_response(response)
            if detection_result:
                driver, driver_name = detection_result
            else:
                # Fallback to openai if available
                if "openai" in self._drivers:
                    driver = self._drivers["openai"]
                    driver_name = "openai"

        if driver is None:
            # Return error result for detection failure
            return [
                ToolResult(
                    id="detection_error",
                    result=None,
                    error="Unable to detect response protocol and no default driver available",
                    meta={"error_code": "PROTOCOL_DETECTION_FAILED"},
                )
            ]

        # Parse response
        try:
            calls = driver.parse(response)
        except Exception as e:
            return [
                ToolResult(
                    id="parse_error",
                    result=None,
                    error=str(e),
                    meta={"error_code": "PARSE_ERROR", "driver": driver_name},
                )
            ]

        # Apply tool filter and enrich context
        results: List[ToolResult] = []
        allowed_calls: List[ToolCall] = []

        for call in calls:
            # Enrich with context
            if context:
                call.context.update(context)

            # Apply filter
            if tool_filter is not None:
                # Check if filter matches this tool call
                metadata = self.get(call.name)
                if metadata is None:
                    results.append(
                        ToolResult(
                            id=call.id,
                            result=None,
                            error=f"Tool '{call.name}' is not registered",
                            meta={"error_code": "TOOL_NOT_FOUND", "filter": repr(tool_filter)},
                        )
                    )
                    continue
                if not tool_filter.matches(metadata):
                    # Denied by filter
                    results.append(
                        ToolResult(
                            id=call.id,
                            result=None,
                            error=f"Tool '{call.name}' denied by filter",
                            meta={"error_code": "FILTER_DENIED", "filter": repr(tool_filter)},
                        )
                    )
                    continue

            allowed_calls.append(call)

        # Execute allowed calls
        if allowed_calls:
            execution_results = await execute_tool_calls(self, allowed_calls)
            results.extend(execution_results)

        # Sort results to maintain original call order
        call_id_order = {call.id: i for i, call in enumerate(calls)}
        results.sort(key=lambda r: call_id_order.get(r.id, len(calls)))

        return results

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
        exclude: Optional[List[str]] = None,
        middlewares: Optional[List[MiddlewareObj]] = None,
    ) -> Callable[[type], type]:
        """
        Decorator to register all methods of a class as tools.

        Args:
            prefix: Optional prefix for tool names.
            tags: Optional tags applied to all methods.
            exclude: Optional list of method names to exclude from registration.
            middlewares: Optional list of middlewares to apply to all registered methods.

        Returns:
            A class decorator.
        """
        from uni_tool.decorators.bind import create_bind_decorator

        return create_bind_decorator(
            self,
            prefix=prefix,
            tags=tags,
            exclude=exclude,
            middlewares=middlewares,
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
