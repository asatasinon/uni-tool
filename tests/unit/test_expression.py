"""
Unit tests for ToolExpression filtering.

Tests cover:
- Tag filtering
- Prefix filtering
- Logical operations (And, Or, Not)
- Combined expressions
"""

from uni_tool.filters import Prefix, Tag
from uni_tool.core.models import ToolMetadata


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
