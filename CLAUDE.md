# Development Guide

## Package Management
**`uv` is used for package management.**

```sh
# install package
uv add <package_name>

# activate virtual environment
source .venv/bin/activate

# run script
uv run <script>
```

## Development Guidelines (from Constitution)

1.  **Protocol Agnosticism**: Core logic MUST be decoupled from specific LLM providers (OpenAI, Anthropic). All protocol-specific transformations happen in the Driver Layer.
2.  **Defense in Depth**: Execution MUST pass through Query (filtering), Filter (permission), and Middleware (runtime isolation).
3.  **Context Isolation**: Sensitive context (User ID, Token) MUST be injected via `Injected` pattern, not passed as direct parameters to LLM.
4.  **Middleware Governance**: Cross-cutting concerns (logging, auth) MUST be implemented as independent Middlewares.
5.  **Spec-Driven**: New features MUST follow the `/speckit` workflow (Init -> Spec -> Plan -> Tasks -> Impl).

## Common Commands

```sh
# Run all tests
uv run pytest

# Run unit tests
uv run pytest tests/unit

# Run integration tests
uv run pytest tests/integration

# Tool Expression Development Workflow
# Test expression logic
uv run pytest tests/unit/test_expression.py

# Middleware Development Workflow
# Test middleware logic
uv run pytest tests/unit/test_middleware.py
```

## Technical Context

**before implement, need to use `context7 mcp tools` to get latest technical context.**
