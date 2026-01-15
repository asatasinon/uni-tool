"""
Docstring parsing utilities for UniTools SDK.

Uses docstring_parser to extract function descriptions and parameter documentation.
"""

from typing import Dict, Optional, Callable, Any
from docstring_parser import parse as parse_docstring, Docstring


def extract_description(func: Callable[..., Any]) -> str:
    """
    Extract the short description from a function's docstring.

    Args:
        func: The function to extract description from.

    Returns:
        The short description, or empty string if not available.
    """
    docstring = func.__doc__
    if not docstring:
        return ""

    parsed: Docstring = parse_docstring(docstring)
    return parsed.short_description or ""


def extract_long_description(func: Callable[..., Any]) -> Optional[str]:
    """
    Extract the long description from a function's docstring.

    Args:
        func: The function to extract description from.

    Returns:
        The long description, or None if not available.
    """
    docstring = func.__doc__
    if not docstring:
        return None

    parsed: Docstring = parse_docstring(docstring)
    return parsed.long_description


def extract_param_descriptions(func: Callable[..., Any]) -> Dict[str, str]:
    """
    Extract parameter descriptions from a function's docstring.

    Args:
        func: The function to extract parameter descriptions from.

    Returns:
        A dictionary mapping parameter names to their descriptions.
    """
    docstring = func.__doc__
    if not docstring:
        return {}

    parsed: Docstring = parse_docstring(docstring)
    return {param.arg_name: param.description or "" for param in parsed.params if param.arg_name}


def extract_return_description(func: Callable[..., Any]) -> Optional[str]:
    """
    Extract the return description from a function's docstring.

    Args:
        func: The function to extract return description from.

    Returns:
        The return description, or None if not available.
    """
    docstring = func.__doc__
    if not docstring:
        return None

    parsed: Docstring = parse_docstring(docstring)
    if parsed.returns:
        return parsed.returns.description
    return None
