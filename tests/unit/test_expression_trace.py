"""
Unit tests for expression diagnostics (ExpressionTrace).

Tests cover:
- Diagnostic trace for atomic expressions (Tag, Prefix, ToolName)
- Diagnostic trace for composite expressions (And, Or, Not)
- Failure reasons and match paths
- Complex nested expression diagnostics
"""

import pytest

from uni_tool.core.expressions import ExpressionTrace
from uni_tool.core.models import ToolMetadata
from uni_tool.filters import Prefix, Tag, ToolName


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


class TestTagDiagnose:
    """Tests for Tag expression diagnostics."""

    def test_tag_match_trace(self):
        """Test diagnostic trace when tag matches."""
        metadata = create_mock_metadata("tool1", tags={"finance", "read"})
        expr = Tag("finance")

        trace = expr.diagnose(metadata)

        assert trace.matched is True
        assert trace.node == "Tag"
        assert "finance" in trace.detail
        assert "found" in trace.detail.lower()
        assert trace.children == []

    def test_tag_no_match_trace(self):
        """Test diagnostic trace when tag doesn't match."""
        metadata = create_mock_metadata("tool1", tags={"admin"})
        expr = Tag("finance")

        trace = expr.diagnose(metadata)

        assert trace.matched is False
        assert trace.node == "Tag"
        assert "finance" in trace.detail
        assert "not" in trace.detail.lower()
        assert trace.children == []

    def test_tag_empty_tags_trace(self):
        """Test diagnostic trace with empty tags."""
        metadata = create_mock_metadata("tool1", tags=set())
        expr = Tag("any")

        trace = expr.diagnose(metadata)

        assert trace.matched is False
        assert trace.node == "Tag"


class TestPrefixDiagnose:
    """Tests for Prefix expression diagnostics."""

    def test_prefix_match_trace(self):
        """Test diagnostic trace when prefix matches."""
        metadata = create_mock_metadata("api_get_user")
        expr = Prefix("api_")

        trace = expr.diagnose(metadata)

        assert trace.matched is True
        assert trace.node == "Prefix"
        assert "api_" in trace.detail
        assert "start" in trace.detail.lower()
        assert trace.children == []

    def test_prefix_no_match_trace(self):
        """Test diagnostic trace when prefix doesn't match."""
        metadata = create_mock_metadata("internal_func")
        expr = Prefix("api_")

        trace = expr.diagnose(metadata)

        assert trace.matched is False
        assert trace.node == "Prefix"
        assert "api_" in trace.detail
        assert "not" in trace.detail.lower() or "does not" in trace.detail.lower()


class TestToolNameDiagnose:
    """Tests for ToolName expression diagnostics."""

    def test_name_match_trace(self):
        """Test diagnostic trace when name matches exactly."""
        metadata = create_mock_metadata("get_user")
        expr = ToolName("get_user")

        trace = expr.diagnose(metadata)

        assert trace.matched is True
        assert trace.node == "ToolName"
        assert "get_user" in trace.detail
        assert "equal" in trace.detail.lower()

    def test_name_no_match_trace(self):
        """Test diagnostic trace when name doesn't match."""
        metadata = create_mock_metadata("get_user")
        expr = ToolName("delete_user")

        trace = expr.diagnose(metadata)

        assert trace.matched is False
        assert trace.node == "ToolName"
        assert "delete_user" in trace.detail


class TestAndDiagnose:
    """Tests for And expression diagnostics."""

    def test_and_both_match_trace(self):
        """Test diagnostic trace when both conditions match."""
        metadata = create_mock_metadata("api_tool", tags={"finance", "read"})
        expr = Tag("finance") & Tag("read")

        trace = expr.diagnose(metadata)

        assert trace.matched is True
        assert trace.node == "And"
        assert "both" in trace.detail.lower()
        assert len(trace.children) == 2
        assert trace.children[0].matched is True
        assert trace.children[1].matched is True

    def test_and_left_fails_trace(self):
        """Test diagnostic trace when left condition fails."""
        metadata = create_mock_metadata("tool", tags={"read"})
        expr = Tag("finance") & Tag("read")

        trace = expr.diagnose(metadata)

        assert trace.matched is False
        assert trace.node == "And"
        assert "left" in trace.detail.lower()
        assert len(trace.children) == 2
        assert trace.children[0].matched is False  # finance fails
        assert trace.children[1].matched is True  # read passes

    def test_and_right_fails_trace(self):
        """Test diagnostic trace when right condition fails."""
        metadata = create_mock_metadata("tool", tags={"finance"})
        expr = Tag("finance") & Tag("read")

        trace = expr.diagnose(metadata)

        assert trace.matched is False
        assert trace.node == "And"
        assert "right" in trace.detail.lower()
        assert len(trace.children) == 2
        assert trace.children[0].matched is True  # finance passes
        assert trace.children[1].matched is False  # read fails

    def test_and_both_fail_trace(self):
        """Test diagnostic trace when both conditions fail."""
        metadata = create_mock_metadata("tool", tags=set())
        expr = Tag("finance") & Tag("read")

        trace = expr.diagnose(metadata)

        assert trace.matched is False
        assert trace.node == "And"
        assert "both" in trace.detail.lower()
        assert len(trace.children) == 2
        assert trace.children[0].matched is False
        assert trace.children[1].matched is False


class TestOrDiagnose:
    """Tests for Or expression diagnostics."""

    def test_or_both_match_trace(self):
        """Test diagnostic trace when both conditions match."""
        metadata = create_mock_metadata("tool", tags={"finance", "admin"})
        expr = Tag("finance") | Tag("admin")

        trace = expr.diagnose(metadata)

        assert trace.matched is True
        assert trace.node == "Or"
        assert "both" in trace.detail.lower()
        assert len(trace.children) == 2

    def test_or_left_only_match_trace(self):
        """Test diagnostic trace when only left condition matches."""
        metadata = create_mock_metadata("tool", tags={"finance"})
        expr = Tag("finance") | Tag("admin")

        trace = expr.diagnose(metadata)

        assert trace.matched is True
        assert trace.node == "Or"
        assert "left" in trace.detail.lower()
        assert len(trace.children) == 2
        assert trace.children[0].matched is True
        assert trace.children[1].matched is False

    def test_or_right_only_match_trace(self):
        """Test diagnostic trace when only right condition matches."""
        metadata = create_mock_metadata("tool", tags={"admin"})
        expr = Tag("finance") | Tag("admin")

        trace = expr.diagnose(metadata)

        assert trace.matched is True
        assert trace.node == "Or"
        assert "right" in trace.detail.lower()
        assert len(trace.children) == 2
        assert trace.children[0].matched is False
        assert trace.children[1].matched is True

    def test_or_both_fail_trace(self):
        """Test diagnostic trace when both conditions fail."""
        metadata = create_mock_metadata("tool", tags=set())
        expr = Tag("finance") | Tag("admin")

        trace = expr.diagnose(metadata)

        assert trace.matched is False
        assert trace.node == "Or"
        assert "neither" in trace.detail.lower()
        assert len(trace.children) == 2


class TestNotDiagnose:
    """Tests for Not expression diagnostics."""

    def test_not_inverts_match_trace(self):
        """Test diagnostic trace when NOT inverts a match."""
        metadata = create_mock_metadata("tool", tags={"deprecated"})
        expr = ~Tag("deprecated")

        trace = expr.diagnose(metadata)

        assert trace.matched is False
        assert trace.node == "Not"
        assert "inner condition matched" in trace.detail.lower()
        assert len(trace.children) == 1
        assert trace.children[0].matched is True

    def test_not_inverts_no_match_trace(self):
        """Test diagnostic trace when NOT inverts a non-match."""
        metadata = create_mock_metadata("tool", tags={"active"})
        expr = ~Tag("deprecated")

        trace = expr.diagnose(metadata)

        assert trace.matched is True
        assert trace.node == "Not"
        assert "inner condition failed" in trace.detail.lower()
        assert len(trace.children) == 1
        assert trace.children[0].matched is False


class TestComplexDiagnose:
    """Tests for complex expression diagnostics."""

    def test_complex_expression_trace_structure(self):
        """Test that complex expressions have proper trace structure."""
        metadata = create_mock_metadata("api_tool", tags={"finance", "read"})
        # (finance & read) | admin
        expr = (Tag("finance") & Tag("read")) | Tag("admin")

        trace = expr.diagnose(metadata)

        # Should match via left branch (finance & read)
        assert trace.matched is True
        assert trace.node == "Or"
        assert len(trace.children) == 2

        # Left child is And
        and_trace = trace.children[0]
        assert and_trace.node == "And"
        assert and_trace.matched is True
        assert len(and_trace.children) == 2

        # Right child is Tag (admin - doesn't match)
        admin_trace = trace.children[1]
        assert admin_trace.node == "Tag"
        assert admin_trace.matched is False

    def test_deep_nested_trace(self):
        """Test deeply nested expression trace."""
        metadata = create_mock_metadata("api_tool", tags={"finance"})
        # ~(~finance) should match
        expr = ~(~Tag("finance"))

        trace = expr.diagnose(metadata)

        assert trace.matched is True
        assert trace.node == "Not"
        assert len(trace.children) == 1

        inner_not = trace.children[0]
        assert inner_not.node == "Not"
        assert inner_not.matched is False

        innermost = inner_not.children[0]
        assert innermost.node == "Tag"
        assert innermost.matched is True

    def test_trace_explains_rejection_reason(self):
        """Test that trace properly explains why a tool was rejected."""
        # Tool has finance but deprecated
        metadata = create_mock_metadata("old_finance", tags={"finance", "deprecated"})
        # Want: finance & ~deprecated (should fail)
        expr = Tag("finance") & ~Tag("deprecated")

        trace = expr.diagnose(metadata)

        assert trace.matched is False
        assert trace.node == "And"

        # Find the failing part
        left_trace = trace.children[0]  # Tag("finance") - passes
        right_trace = trace.children[1]  # ~Tag("deprecated") - fails

        assert left_trace.matched is True
        assert right_trace.matched is False
        assert right_trace.node == "Not"

        # The innermost trace shows deprecated was found
        deprecated_trace = right_trace.children[0]
        assert deprecated_trace.matched is True
        assert deprecated_trace.node == "Tag"


class TestExpressionTraceDataclass:
    """Tests for ExpressionTrace dataclass behavior."""

    def test_trace_is_frozen(self):
        """Test that ExpressionTrace is immutable (frozen dataclass)."""
        trace = ExpressionTrace(
            matched=True,
            node="Test",
            detail="test detail",
            children=[],
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            trace.matched = False

    def test_trace_equality(self):
        """Test ExpressionTrace equality comparison."""
        trace1 = ExpressionTrace(matched=True, node="Tag", detail="test", children=[])
        trace2 = ExpressionTrace(matched=True, node="Tag", detail="test", children=[])

        assert trace1 == trace2

    def test_trace_repr(self):
        """Test ExpressionTrace has readable repr."""
        trace = ExpressionTrace(
            matched=True,
            node="Tag",
            detail="Tag 'finance' found",
            children=[],
        )

        repr_str = repr(trace)
        assert "ExpressionTrace" in repr_str
        assert "matched=True" in repr_str
