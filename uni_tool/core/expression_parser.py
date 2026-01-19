"""
DSL Expression Parser for UniTools SDK.

Parses DSL strings into ToolExpression trees using Lark.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lark import Lark, Transformer
from lark.exceptions import UnexpectedInput, VisitError

from uni_tool.core.errors import ExpressionParseError
from uni_tool.core.expressions import And, Not, Or, ToolExpression
from uni_tool.filters import Prefix, Tag, ToolName

if TYPE_CHECKING:
    pass


# Lark grammar for expression DSL
# Precedence (lowest to highest): OR < AND < NOT < ATOM
GRAMMAR = r"""
    ?start: or_expr

    ?or_expr: and_expr
            | or_expr "|" and_expr -> or_op

    ?and_expr: not_expr
             | and_expr "&" not_expr -> and_op

    ?not_expr: atom
             | "~" not_expr -> not_op

    ?atom: "(" or_expr ")"
         | TAG_LITERAL
         | PREFIX_LITERAL
         | NAME_LITERAL
         | CARET_LITERAL
         | BACKTICK_LITERAL
         | IDENTIFIER -> bare_identifier

    // Compound terminals for typed expressions - defined first for priority
    TAG_LITERAL.2: /tag:[A-Za-z_][A-Za-z0-9_\-]*/
    PREFIX_LITERAL.2: /prefix:[A-Za-z_][A-Za-z0-9_\-]*/
    NAME_LITERAL.2: /name:[A-Za-z_][A-Za-z0-9_\-]*/
    CARET_LITERAL.2: /\^[A-Za-z_][A-Za-z0-9_\-]*/
    BACKTICK_LITERAL.2: /`[A-Za-z_][A-Za-z0-9_\-]*`/

    // Bare identifier (tag fallback)
    IDENTIFIER: /[A-Za-z_][A-Za-z0-9_\-]*/

    %import common.WS
    %ignore WS
"""

# Maximum allowed expression nesting depth
MAX_DEPTH = 50


class ExpressionTransformer(Transformer):
    """Transform parse tree into ToolExpression objects."""

    def __init__(self):
        super().__init__()
        self._depth = 0

    def or_op(self, items) -> Or:
        """Create Or expression."""
        # items = [left, right]
        return Or(items[0], items[1])

    def and_op(self, items) -> And:
        """Create And expression."""
        # items = [left, right]
        return And(items[0], items[1])

    def not_op(self, items) -> Not:
        """Create Not expression."""
        # items = [expr]
        return Not(items[0])

    def bare_identifier(self, items) -> Tag:
        """Bare identifier is treated as tag."""
        # items = [identifier token]
        return Tag(str(items[0]))

    def TAG_LITERAL(self, token) -> Tag:
        """Handle tag:name literal."""
        # token value is "tag:name", extract the name part
        value = str(token)
        name = value[4:]  # Remove "tag:" prefix
        return Tag(name)

    def PREFIX_LITERAL(self, token) -> Prefix:
        """Handle prefix:value literal."""
        # token value is "prefix:value", extract the value part
        value = str(token)
        prefix = value[7:]  # Remove "prefix:" prefix
        return Prefix(prefix)

    def NAME_LITERAL(self, token) -> ToolName:
        """Handle name:value literal."""
        # token value is "name:value", extract the value part
        value = str(token)
        name = value[5:]  # Remove "name:" prefix
        return ToolName(name)

    def CARET_LITERAL(self, token) -> Prefix:
        """Handle ^prefix shorthand."""
        # token value is "^prefix", extract the prefix part
        value = str(token)
        prefix = value[1:]  # Remove "^" prefix
        return Prefix(prefix)

    def BACKTICK_LITERAL(self, token) -> ToolName:
        """Handle `name` shorthand."""
        # token value is "`name`", extract the name part
        value = str(token)
        name = value[1:-1]  # Remove surrounding backticks
        return ToolName(name)

    def IDENTIFIER(self, token) -> str:
        """Return identifier value."""
        return str(token)


class ExpressionParser:
    """
    Parser for DSL expression strings.

    Converts DSL strings into ToolExpression trees.

    Syntax:
        - `tag` or `tag:name` - Tag filter
        - `prefix:api_` - Prefix filter
        - `name:tool_name` - Exact name filter
        - `^api_` - Shorthand for prefix:api_
        - `` `tool_name` `` - Shorthand for name:tool_name
        - `|` - OR operator
        - `&` - AND operator
        - `~` - NOT operator
        - `(...)` - Grouping
    """

    def __init__(self):
        self._parser = Lark(
            GRAMMAR,
            parser="lalr",
            transformer=ExpressionTransformer(),
        )

    def parse(self, text: str) -> ToolExpression:
        """
        Parse a DSL string into a ToolExpression.

        Args:
            text: The DSL string to parse.

        Returns:
            A ToolExpression tree.

        Raises:
            ExpressionParseError: If the DSL string is invalid.
        """
        if not text or not text.strip():
            raise ExpressionParseError(
                "Empty expression",
                line=1,
                column=1,
                context=text or "<empty>",
            )

        # Check for depth limit
        depth = self._calculate_depth(text)
        if depth > MAX_DEPTH:
            raise ExpressionParseError(
                f"Expression depth ({depth}) exceeds maximum ({MAX_DEPTH})",
                line=1,
                column=1,
                context=text[:50] + "..." if len(text) > 50 else text,
            )

        try:
            result = self._parser.parse(text)
            if not isinstance(result, ToolExpression):
                raise ExpressionParseError(
                    "Failed to parse expression",
                    line=1,
                    column=1,
                    context=text,
                )
            return result
        except UnexpectedInput as e:
            context = e.get_context(text) if hasattr(e, "get_context") else text
            raise ExpressionParseError(
                str(e.args[0]) if e.args else "Unexpected input",
                line=getattr(e, "line", 1),
                column=getattr(e, "column", 1),
                context=context,
            ) from e
        except VisitError as e:
            # Extract the original exception from VisitError
            original = e.orig_exc if hasattr(e, "orig_exc") else e
            raise ExpressionParseError(
                str(original),
                line=1,
                column=1,
                context=text,
            ) from e

    def _calculate_depth(self, text: str) -> int:
        """Calculate the nesting depth of parentheses."""
        max_depth = 0
        current_depth = 0
        for char in text:
            if char == "(":
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ")":
                current_depth -= 1
        return max_depth
