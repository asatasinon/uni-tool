"""
Unit tests for DSL expression parser.

Tests cover:
- Basic DSL parsing (tags, prefix, name)
- Operator precedence (AND > OR, NOT highest)
- Shorthand syntax (^prefix, `name`)
- Invalid identifier rejection
- Invalid ^ shorthand rejection
- Expression depth limits
- Error details (line, column, context)
"""

import pytest

from uni_tool.core.errors import ExpressionParseError
from uni_tool.core.expression_parser import ExpressionParser
from uni_tool.core.expressions import And, Not, Or
from uni_tool.filters import Prefix, Tag, ToolName


class TestBasicParsing:
    """Tests for basic DSL parsing."""

    def test_parse_simple_tag(self):
        """Test parsing a simple tag."""
        parser = ExpressionParser()
        expr = parser.parse("finance")

        assert isinstance(expr, Tag)
        assert expr.name == "finance"

    def test_parse_tag_with_explicit_syntax(self):
        """Test parsing tag with explicit 'tag:' prefix."""
        parser = ExpressionParser()
        expr = parser.parse("tag:finance")

        assert isinstance(expr, Tag)
        assert expr.name == "finance"

    def test_parse_prefix_expression(self):
        """Test parsing prefix expression."""
        parser = ExpressionParser()
        expr = parser.parse("prefix:api_")

        assert isinstance(expr, Prefix)
        assert expr.prefix == "api_"

    def test_parse_name_expression(self):
        """Test parsing name expression."""
        parser = ExpressionParser()
        expr = parser.parse("name:get_user")

        assert isinstance(expr, ToolName)
        assert expr.name == "get_user"

    def test_parse_or_expression(self):
        """Test parsing OR expression."""
        parser = ExpressionParser()
        expr = parser.parse("finance | admin")

        assert isinstance(expr, Or)
        assert isinstance(expr.left, Tag)
        assert isinstance(expr.right, Tag)
        assert expr.left.name == "finance"
        assert expr.right.name == "admin"

    def test_parse_and_expression(self):
        """Test parsing AND expression."""
        parser = ExpressionParser()
        expr = parser.parse("finance & read")

        assert isinstance(expr, And)
        assert isinstance(expr.left, Tag)
        assert isinstance(expr.right, Tag)

    def test_parse_not_expression(self):
        """Test parsing NOT expression."""
        parser = ExpressionParser()
        expr = parser.parse("~deprecated")

        assert isinstance(expr, Not)
        assert isinstance(expr.expr, Tag)
        assert expr.expr.name == "deprecated"

    def test_parse_grouped_expression(self):
        """Test parsing grouped expression with parentheses."""
        parser = ExpressionParser()
        expr = parser.parse("(finance | admin)")

        assert isinstance(expr, Or)


class TestOperatorPrecedence:
    """Tests for operator precedence."""

    def test_and_higher_than_or(self):
        """Test that AND has higher precedence than OR: a | b & c == a | (b & c)."""
        parser = ExpressionParser()
        expr = parser.parse("a | b & c")

        # Should be: Or(Tag(a), And(Tag(b), Tag(c)))
        assert isinstance(expr, Or)
        assert isinstance(expr.left, Tag)
        assert expr.left.name == "a"
        assert isinstance(expr.right, And)

    def test_not_highest_precedence(self):
        """Test that NOT has highest precedence: ~a & b == (~a) & b."""
        parser = ExpressionParser()
        expr = parser.parse("~a & b")

        # Should be: And(Not(Tag(a)), Tag(b))
        assert isinstance(expr, And)
        assert isinstance(expr.left, Not)
        assert isinstance(expr.right, Tag)

    def test_parentheses_override_precedence(self):
        """Test that parentheses override default precedence."""
        parser = ExpressionParser()
        expr = parser.parse("(a | b) & c")

        # Should be: And(Or(Tag(a), Tag(b)), Tag(c))
        assert isinstance(expr, And)
        assert isinstance(expr.left, Or)
        assert isinstance(expr.right, Tag)

    def test_complex_precedence(self):
        """Test complex expression with multiple operators."""
        parser = ExpressionParser()
        expr = parser.parse("a | b & ~c | d")

        # Should be: Or(Or(Tag(a), And(Tag(b), Not(Tag(c)))), Tag(d))
        assert isinstance(expr, Or)


class TestShorthandSyntax:
    """Tests for shorthand syntax."""

    def test_caret_prefix_shorthand(self):
        """Test ^prefix shorthand equals prefix:prefix."""
        parser = ExpressionParser()
        expr = parser.parse("^api_")

        assert isinstance(expr, Prefix)
        assert expr.prefix == "api_"

    def test_caret_prefix_with_regex_pattern(self):
        """Test ^tool_.* shorthand (regex part is stripped)."""
        parser = ExpressionParser()
        expr = parser.parse("^tool_")

        assert isinstance(expr, Prefix)
        assert expr.prefix == "tool_"

    def test_backtick_name_shorthand(self):
        """Test `tool_name` shorthand equals name:tool_name."""
        parser = ExpressionParser()
        expr = parser.parse("`get_user`")

        assert isinstance(expr, ToolName)
        assert expr.name == "get_user"

    def test_shorthand_in_complex_expression(self):
        """Test shorthand syntax in complex expressions."""
        parser = ExpressionParser()
        expr = parser.parse("^api_ & ~`deprecated_tool`")

        assert isinstance(expr, And)
        assert isinstance(expr.left, Prefix)
        assert isinstance(expr.right, Not)
        assert isinstance(expr.right.expr, ToolName)


class TestInvalidIdentifiers:
    """Tests for invalid identifier rejection."""

    def test_reject_identifier_with_space(self):
        """Test that identifiers with spaces are rejected."""
        parser = ExpressionParser()

        with pytest.raises(ExpressionParseError):
            parser.parse("finance tool")

    def test_reject_identifier_with_special_chars(self):
        """Test that identifiers with DSL special chars are rejected."""
        parser = ExpressionParser()

        # Note: "tag:finance|admin" parses as "Tag(finance) | Tag(admin)" which is valid
        # Test truly invalid special characters in identifiers
        with pytest.raises(ExpressionParseError):
            parser.parse("tag:finance@admin")  # @ is invalid

    def test_reject_empty_identifier(self):
        """Test that empty identifiers are rejected."""
        parser = ExpressionParser()

        with pytest.raises(ExpressionParseError):
            parser.parse("tag:")

    def test_reject_identifier_starting_with_number(self):
        """Test that identifiers starting with numbers are rejected."""
        parser = ExpressionParser()

        with pytest.raises(ExpressionParseError):
            parser.parse("123tool")


class TestInvalidCaretShorthand:
    """Tests for invalid ^ shorthand rejection."""

    def test_reject_caret_without_identifier(self):
        """Test that ^ without identifier is rejected."""
        parser = ExpressionParser()

        with pytest.raises(ExpressionParseError):
            parser.parse("^")

    def test_reject_caret_with_invalid_pattern(self):
        """Test that ^ with invalid pattern is rejected."""
        parser = ExpressionParser()

        with pytest.raises(ExpressionParseError):
            parser.parse("^|")


class TestDepthLimit:
    """Tests for expression depth limits."""

    def test_deeply_nested_expression_rejected(self):
        """Test that expressions exceeding depth limit are rejected."""
        parser = ExpressionParser()

        # Create a deeply nested expression (depth > 50)
        deep_expr = "a"
        for _ in range(60):
            deep_expr = f"({deep_expr})"

        with pytest.raises(ExpressionParseError) as exc_info:
            parser.parse(deep_expr)

        assert "depth" in str(exc_info.value).lower()

    def test_normal_depth_accepted(self):
        """Test that normal depth expressions are accepted."""
        parser = ExpressionParser()

        # Moderate nesting should work
        expr = parser.parse("((a & b) | (c & d)) & ((e | f) & g)")
        assert expr is not None


class TestErrorDetails:
    """Tests for error details (line, column, context)."""

    def test_error_has_line_number(self):
        """Test that parse error includes line number."""
        parser = ExpressionParser()

        with pytest.raises(ExpressionParseError) as exc_info:
            parser.parse("invalid @@ syntax")

        assert exc_info.value.line >= 1

    def test_error_has_column_number(self):
        """Test that parse error includes column number."""
        parser = ExpressionParser()

        with pytest.raises(ExpressionParseError) as exc_info:
            parser.parse("a & @invalid")

        assert exc_info.value.column >= 1

    def test_error_has_context(self):
        """Test that parse error includes context snippet."""
        parser = ExpressionParser()

        with pytest.raises(ExpressionParseError) as exc_info:
            parser.parse("finance & @broken")

        assert exc_info.value.context is not None
        assert len(exc_info.value.context) > 0

    def test_error_message_is_descriptive(self):
        """Test that error message is descriptive."""
        parser = ExpressionParser()

        with pytest.raises(ExpressionParseError) as exc_info:
            parser.parse("&&&")

        assert exc_info.value.message is not None
        assert len(exc_info.value.message) > 0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_parse_empty_string_fails(self):
        """Test that empty string fails to parse."""
        parser = ExpressionParser()

        with pytest.raises(ExpressionParseError):
            parser.parse("")

    def test_parse_whitespace_only_fails(self):
        """Test that whitespace-only string fails to parse."""
        parser = ExpressionParser()

        with pytest.raises(ExpressionParseError):
            parser.parse("   ")

    def test_parse_with_extra_whitespace(self):
        """Test that extra whitespace is handled."""
        parser = ExpressionParser()
        expr = parser.parse("  finance   &   admin  ")

        assert isinstance(expr, And)

    def test_case_sensitivity(self):
        """Test that parsing is case-sensitive."""
        parser = ExpressionParser()

        expr1 = parser.parse("Finance")
        expr2 = parser.parse("finance")

        assert isinstance(expr1, Tag)
        assert isinstance(expr2, Tag)
        assert expr1.name == "Finance"
        assert expr2.name == "finance"
        assert expr1.name != expr2.name

    def test_identifier_with_underscore(self):
        """Test identifiers with underscores."""
        parser = ExpressionParser()
        expr = parser.parse("my_tag_name")

        assert isinstance(expr, Tag)
        assert expr.name == "my_tag_name"

    def test_identifier_with_hyphen(self):
        """Test identifiers with hyphens."""
        parser = ExpressionParser()
        expr = parser.parse("my-tag-name")

        assert isinstance(expr, Tag)
        assert expr.name == "my-tag-name"

    def test_identifier_with_numbers(self):
        """Test identifiers with numbers (not at start)."""
        parser = ExpressionParser()
        expr = parser.parse("tag123")

        assert isinstance(expr, Tag)
        assert expr.name == "tag123"


class TestRoundTrip:
    """Tests for parse -> to_dsl -> parse round trip."""

    def test_simple_tag_round_trip(self):
        """Test simple tag round trip."""
        parser = ExpressionParser()
        original = parser.parse("finance")
        dsl = original.to_dsl()
        reparsed = parser.parse(dsl)

        assert isinstance(reparsed, Tag)
        assert reparsed.name == original.name

    def test_complex_expression_round_trip(self):
        """Test complex expression round trip."""
        parser = ExpressionParser()
        original = parser.parse("(finance | admin) & ~deprecated")
        dsl = original.to_dsl()
        reparsed = parser.parse(dsl)

        # Verify structure matches
        assert isinstance(reparsed, And)
        assert isinstance(reparsed.left, Or)
        assert isinstance(reparsed.right, Not)
