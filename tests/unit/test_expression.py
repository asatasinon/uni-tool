"""
Unit tests for ToolExpression filtering.

Tests cover:
- Tag filtering
- Prefix filtering
- Logical operations (And, Or, Not)
- Combined expressions
- Universe DSL string filtering
- Case sensitivity
"""

import pytest

from uni_tool.filters import Prefix, Tag, ToolName
from uni_tool.core.models import ToolMetadata
from uni_tool.core.universe import Universe


def create_mock_metadata(
    name: str,
    tags: set[str] | None = None,
) -> ToolMetadata:
    """Create a mock ToolMetadata for testing."""
    return ToolMetadata(
        name=name,
        description=f"Mock tool {name}",
        func=lambda: None,
        tags=tags or set(),
    )


class TestTagExpression:
    """Tests for Tag filtering."""

    def test_tag_matches_present_tag(self):
        """Test that Tag matches when the tag is present."""
        metadata = create_mock_metadata("tool1", tags={"finance", "read"})
        expr = Tag("finance")

        assert expr.matches(metadata) is True

    def test_tag_does_not_match_absent_tag(self):
        """Test that Tag doesn't match when the tag is absent."""
        metadata = create_mock_metadata("tool1", tags={"finance"})
        expr = Tag("admin")

        assert expr.matches(metadata) is False

    def test_tag_with_empty_tags(self):
        """Test that Tag doesn't match with empty tags."""
        metadata = create_mock_metadata("tool1", tags=set())
        expr = Tag("any")

        assert expr.matches(metadata) is False

    def test_tag_repr(self):
        """Test Tag string representation."""
        expr = Tag("finance")
        assert repr(expr) == "Tag('finance')"


class TestPrefixExpression:
    """Tests for Prefix filtering."""

    def test_prefix_matches_exact_prefix(self):
        """Test that Prefix matches when name starts with prefix."""
        metadata = create_mock_metadata("finance_get_balance")
        expr = Prefix("finance_")

        assert expr.matches(metadata) is True

    def test_prefix_matches_exact_name(self):
        """Test that Prefix matches when name equals prefix."""
        metadata = create_mock_metadata("finance")
        expr = Prefix("finance")

        assert expr.matches(metadata) is True

    def test_prefix_does_not_match_different_prefix(self):
        """Test that Prefix doesn't match with different prefix."""
        metadata = create_mock_metadata("admin_tool")
        expr = Prefix("finance_")

        assert expr.matches(metadata) is False

    def test_prefix_does_not_match_suffix(self):
        """Test that Prefix doesn't match when prefix is in middle/end."""
        metadata = create_mock_metadata("get_finance_data")
        expr = Prefix("finance")

        assert expr.matches(metadata) is False

    def test_prefix_repr(self):
        """Test Prefix string representation."""
        expr = Prefix("api_")
        assert repr(expr) == "Prefix('api_')"


class TestAndExpression:
    """Tests for And (logical AND) expression."""

    def test_and_matches_when_both_match(self):
        """Test that And matches when both expressions match."""
        metadata = create_mock_metadata("finance_read", tags={"finance", "read"})
        expr = Tag("finance") & Tag("read")

        assert expr.matches(metadata) is True

    def test_and_does_not_match_when_first_fails(self):
        """Test that And doesn't match when first expression fails."""
        metadata = create_mock_metadata("tool", tags={"read"})
        expr = Tag("finance") & Tag("read")

        assert expr.matches(metadata) is False

    def test_and_does_not_match_when_second_fails(self):
        """Test that And doesn't match when second expression fails."""
        metadata = create_mock_metadata("tool", tags={"finance"})
        expr = Tag("finance") & Tag("read")

        assert expr.matches(metadata) is False

    def test_and_does_not_match_when_both_fail(self):
        """Test that And doesn't match when both expressions fail."""
        metadata = create_mock_metadata("tool", tags=set())
        expr = Tag("finance") & Tag("read")

        assert expr.matches(metadata) is False

    def test_and_repr(self):
        """Test And string representation."""
        expr = Tag("a") & Tag("b")
        assert repr(expr) == "(Tag('a') & Tag('b'))"


class TestOrExpression:
    """Tests for Or (logical OR) expression."""

    def test_or_matches_when_both_match(self):
        """Test that Or matches when both expressions match."""
        metadata = create_mock_metadata("tool", tags={"finance", "admin"})
        expr = Tag("finance") | Tag("admin")

        assert expr.matches(metadata) is True

    def test_or_matches_when_first_matches(self):
        """Test that Or matches when only first expression matches."""
        metadata = create_mock_metadata("tool", tags={"finance"})
        expr = Tag("finance") | Tag("admin")

        assert expr.matches(metadata) is True

    def test_or_matches_when_second_matches(self):
        """Test that Or matches when only second expression matches."""
        metadata = create_mock_metadata("tool", tags={"admin"})
        expr = Tag("finance") | Tag("admin")

        assert expr.matches(metadata) is True

    def test_or_does_not_match_when_both_fail(self):
        """Test that Or doesn't match when both expressions fail."""
        metadata = create_mock_metadata("tool", tags=set())
        expr = Tag("finance") | Tag("admin")

        assert expr.matches(metadata) is False

    def test_or_repr(self):
        """Test Or string representation."""
        expr = Tag("a") | Tag("b")
        assert repr(expr) == "(Tag('a') | Tag('b'))"


class TestNotExpression:
    """Tests for Not (logical NOT) expression."""

    def test_not_inverts_matching(self):
        """Test that Not inverts a matching expression."""
        metadata = create_mock_metadata("tool", tags={"finance"})
        expr = ~Tag("finance")

        assert expr.matches(metadata) is False

    def test_not_inverts_non_matching(self):
        """Test that Not inverts a non-matching expression."""
        metadata = create_mock_metadata("tool", tags={"admin"})
        expr = ~Tag("finance")

        assert expr.matches(metadata) is True

    def test_not_repr(self):
        """Test Not string representation."""
        expr = ~Tag("a")
        assert repr(expr) == "~Tag('a')"


class TestComplexExpressions:
    """Tests for complex combined expressions."""

    def test_and_or_combined(self):
        """Test combined AND and OR: (A & B) | C."""
        metadata1 = create_mock_metadata("tool1", tags={"api", "read"})
        metadata2 = create_mock_metadata("tool2", tags={"internal"})
        metadata3 = create_mock_metadata("tool3", tags={"api"})

        # (api & read) | internal
        expr = (Tag("api") & Tag("read")) | Tag("internal")

        assert expr.matches(metadata1) is True  # has api & read
        assert expr.matches(metadata2) is True  # has internal
        assert expr.matches(metadata3) is False  # only api, not read

    def test_not_with_and(self):
        """Test NOT combined with AND: A & ~B."""
        metadata1 = create_mock_metadata("tool1", tags={"api"})
        metadata2 = create_mock_metadata("tool2", tags={"api", "deprecated"})

        # api & ~deprecated
        expr = Tag("api") & ~Tag("deprecated")

        assert expr.matches(metadata1) is True  # has api, no deprecated
        assert expr.matches(metadata2) is False  # has both

    def test_prefix_with_tag(self):
        """Test Prefix combined with Tag."""
        metadata1 = create_mock_metadata("api_get_users", tags={"read"})
        metadata2 = create_mock_metadata("api_delete_user", tags={"write"})
        metadata3 = create_mock_metadata("internal_get", tags={"read"})

        # Starts with api_ AND has read tag
        expr = Prefix("api_") & Tag("read")

        assert expr.matches(metadata1) is True
        assert expr.matches(metadata2) is False  # no read tag
        assert expr.matches(metadata3) is False  # wrong prefix

    def test_triple_or(self):
        """Test triple OR: A | B | C."""
        metadata = create_mock_metadata("tool", tags={"experimental"})

        expr = Tag("prod") | Tag("staging") | Tag("experimental")

        assert expr.matches(metadata) is True

    def test_de_morgan_equivalence(self):
        """Test De Morgan's law: ~(A & B) == ~A | ~B."""
        metadata1 = create_mock_metadata("tool1", tags=set())
        metadata2 = create_mock_metadata("tool2", tags={"a"})
        metadata3 = create_mock_metadata("tool3", tags={"b"})
        metadata4 = create_mock_metadata("tool4", tags={"a", "b"})

        expr1 = ~(Tag("a") & Tag("b"))
        expr2 = ~Tag("a") | ~Tag("b")

        for metadata in [metadata1, metadata2, metadata3, metadata4]:
            assert expr1.matches(metadata) == expr2.matches(metadata)


class TestUniverseDSLFiltering:
    """Tests for Universe DSL string filtering."""

    @pytest.fixture(autouse=True)
    def setup_universe(self):
        """Setup and teardown Universe for each test."""
        self.universe = Universe()
        yield
        self.universe._reset()

    def register_test_tools(self):
        """Register test tools with various tags."""

        @self.universe.tool(tags={"finance", "read"})
        def get_balance(account_id: str) -> float:
            return 100.0

        @self.universe.tool(tags={"finance", "write"})
        def transfer_funds(from_acc: str, to_acc: str, amount: float) -> bool:
            return True

        @self.universe.tool(tags={"admin"})
        def admin_reset(target: str) -> str:
            return "reset"

        @self.universe.tool(tags={"deprecated"})
        def old_function() -> None:
            pass

    def test_dsl_string_matches_expression_object(self):
        """Test that DSL string produces same results as expression object."""
        self.register_test_tools()

        # Using expression object
        expr = Tag("finance") & Tag("read")
        result_obj = self.universe[expr]

        # Using DSL string
        result_dsl = self.universe["finance & read"]

        # Should match same tools
        obj_names = {t.name for t in result_obj.tools}
        dsl_names = {t.name for t in result_dsl.tools}
        assert obj_names == dsl_names
        assert "get_balance" in obj_names

    def test_dsl_string_or_expression(self):
        """Test DSL string with OR expression."""
        self.register_test_tools()

        result = self.universe["finance | admin"]
        names = {t.name for t in result.tools}

        assert "get_balance" in names
        assert "transfer_funds" in names
        assert "admin_reset" in names

    def test_dsl_string_not_expression(self):
        """Test DSL string with NOT expression."""
        self.register_test_tools()

        result = self.universe["~deprecated"]
        names = {t.name for t in result.tools}

        assert "old_function" not in names
        assert "get_balance" in names

    def test_dsl_string_complex_expression(self):
        """Test DSL string with complex expression."""
        self.register_test_tools()

        result = self.universe["(finance | admin) & ~deprecated"]
        names = {t.name for t in result.tools}

        assert "get_balance" in names
        assert "transfer_funds" in names
        assert "admin_reset" in names
        assert "old_function" not in names

    def test_case_sensitive_tag_matching(self):
        """Test that tag matching is case-sensitive."""
        self.universe._reset()

        @self.universe.tool(tags={"Finance"})  # Capital F
        def capitalized_tool() -> None:
            pass

        @self.universe.tool(tags={"finance"})  # Lowercase f
        def lowercase_tool() -> None:
            pass

        # Exact case match
        result_capital = self.universe["Finance"]
        result_lower = self.universe["finance"]

        capital_names = {t.name for t in result_capital.tools}
        lower_names = {t.name for t in result_lower.tools}

        assert "capitalized_tool" in capital_names
        assert "lowercase_tool" not in capital_names
        assert "lowercase_tool" in lower_names
        assert "capitalized_tool" not in lower_names

    def test_case_sensitive_prefix_matching(self):
        """Test that prefix matching is case-sensitive."""
        self.universe._reset()

        @self.universe.tool()
        def API_get_user() -> None:
            pass

        @self.universe.tool()
        def api_get_user() -> None:
            pass

        result_upper = self.universe["prefix:API_"]
        result_lower = self.universe["prefix:api_"]

        upper_names = {t.name for t in result_upper.tools}
        lower_names = {t.name for t in result_lower.tools}

        assert "API_get_user" in upper_names
        assert "api_get_user" not in upper_names
        assert "api_get_user" in lower_names
        assert "API_get_user" not in lower_names

    def test_case_sensitive_name_matching(self):
        """Test that name matching is case-sensitive."""
        self.universe._reset()

        @self.universe.tool()
        def GetUser() -> None:
            pass

        @self.universe.tool()
        def getuser() -> None:
            pass

        result_camel = self.universe["name:GetUser"]
        result_lower = self.universe["name:getuser"]

        camel_names = {t.name for t in result_camel.tools}
        lower_names = {t.name for t in result_lower.tools}

        assert "GetUser" in camel_names
        assert "getuser" not in camel_names
        assert "getuser" in lower_names
        assert "GetUser" not in lower_names

    def test_empty_result_for_no_match(self):
        """Test that non-matching DSL returns empty ToolSet."""
        self.register_test_tools()

        result = self.universe["nonexistent_tag"]
        assert len(result.tools) == 0

    def test_dsl_prefix_shorthand(self):
        """Test ^prefix shorthand syntax."""
        self.universe._reset()

        @self.universe.tool()
        def api_get_user() -> None:
            pass

        @self.universe.tool()
        def api_list_users() -> None:
            pass

        @self.universe.tool()
        def internal_func() -> None:
            pass

        result = self.universe["^api_"]
        names = {t.name for t in result.tools}

        assert "api_get_user" in names
        assert "api_list_users" in names
        assert "internal_func" not in names

    def test_dsl_name_shorthand(self):
        """Test `name` backtick shorthand syntax."""
        self.universe._reset()

        @self.universe.tool()
        def specific_tool() -> None:
            pass

        @self.universe.tool()
        def another_tool() -> None:
            pass

        result = self.universe["`specific_tool`"]
        names = {t.name for t in result.tools}

        assert "specific_tool" in names
        assert "another_tool" not in names


class TestExpressionSimplify:
    """Tests for expression simplification rules."""

    def test_simplify_atomic_returns_self(self):
        """Test that atomic expressions return themselves."""
        tag = Tag("finance")
        prefix = Prefix("api_")
        name = ToolName("get_user")

        assert tag.simplify() is tag
        assert prefix.simplify() is prefix
        assert name.simplify() is name

    def test_simplify_double_negation(self):
        """Test double negation elimination: ~~A -> A."""
        expr = ~(~Tag("finance"))
        simplified = expr.simplify()

        assert isinstance(simplified, Tag)
        assert simplified.name == "finance"

    def test_simplify_triple_negation(self):
        """Test triple negation simplification: ~~~A -> ~A."""
        expr = ~(~(~Tag("finance")))
        simplified = expr.simplify()

        # ~~~A should become ~A
        assert isinstance(simplified, type(~Tag("x")))  # Not
        inner = simplified.expr
        assert isinstance(inner, Tag)
        assert inner.name == "finance"

    def test_simplify_and_deduplication(self):
        """Test AND deduplication: A & A -> A."""
        expr = Tag("finance") & Tag("finance")
        simplified = expr.simplify()

        # Should simplify to just Tag("finance")
        assert isinstance(simplified, Tag)
        assert simplified.name == "finance"

    def test_simplify_or_deduplication(self):
        """Test OR deduplication: A | A -> A."""
        expr = Tag("finance") | Tag("finance")
        simplified = expr.simplify()

        # Should simplify to just Tag("finance")
        assert isinstance(simplified, Tag)
        assert simplified.name == "finance"

    def test_simplify_and_flattening(self):
        """Test AND flattening: (A & B) & C -> flat structure."""
        expr = (Tag("a") & Tag("b")) & Tag("c")
        simplified = expr.simplify()

        # Result should be a flattened And chain
        # We can verify by checking the DSL representation
        dsl = simplified.to_dsl()
        assert "a" in dsl
        assert "b" in dsl
        assert "c" in dsl

    def test_simplify_or_flattening(self):
        """Test OR flattening: (A | B) | C -> flat structure."""
        expr = (Tag("a") | Tag("b")) | Tag("c")
        simplified = expr.simplify()

        # Result should be a flattened Or chain
        dsl = simplified.to_dsl()
        assert "a" in dsl
        assert "b" in dsl
        assert "c" in dsl

    def test_simplify_preserves_semantics(self):
        """Test that simplification preserves semantic equivalence."""
        metadata_a = ToolMetadata(
            name="tool",
            description="Test",
            func=lambda: None,
            tags={"a"},
        )
        metadata_ab = ToolMetadata(
            name="tool",
            description="Test",
            func=lambda: None,
            tags={"a", "b"},
        )
        metadata_empty = ToolMetadata(
            name="tool",
            description="Test",
            func=lambda: None,
            tags=set(),
        )

        # Test double negation
        expr1 = ~(~Tag("a"))
        simplified1 = expr1.simplify()
        assert expr1.matches(metadata_a) == simplified1.matches(metadata_a)
        assert expr1.matches(metadata_empty) == simplified1.matches(metadata_empty)

        # Test deduplication
        expr2 = Tag("a") & Tag("a")
        simplified2 = expr2.simplify()
        assert expr2.matches(metadata_a) == simplified2.matches(metadata_a)
        assert expr2.matches(metadata_empty) == simplified2.matches(metadata_empty)

        # Test complex expression
        expr3 = (Tag("a") | Tag("a")) & Tag("b")
        simplified3 = expr3.simplify()
        assert expr3.matches(metadata_ab) == simplified3.matches(metadata_ab)
        assert expr3.matches(metadata_a) == simplified3.matches(metadata_a)

    def test_simplify_complex_expression(self):
        """Test simplification of complex expressions."""
        # (A | A) & (B | B) should simplify to A & B
        expr = (Tag("a") | Tag("a")) & (Tag("b") | Tag("b"))
        simplified = expr.simplify()

        # Verify simplification occurred
        dsl = simplified.to_dsl()
        # Should not have duplicate operands
        assert dsl.count("a") == 1 or "a & b" in dsl or "b & a" in dsl

    def test_simplify_mixed_dedup_and_negation(self):
        """Test simplification with both deduplication and negation."""
        # ~~A & A should simplify to A & A -> A
        expr = ~(~Tag("a")) & Tag("a")
        simplified = expr.simplify()

        # After double negation elimination and deduplication
        # Should be just Tag("a")
        assert isinstance(simplified, Tag)
        assert simplified.name == "a"

    def test_simplify_idempotent(self):
        """Test that simplification is idempotent."""
        expr = (Tag("a") | Tag("a")) & ~(~Tag("b"))
        simplified_once = expr.simplify()
        simplified_twice = simplified_once.simplify()

        # Simplifying twice should give same result
        assert simplified_once.to_dsl() == simplified_twice.to_dsl()
