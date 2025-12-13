from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def split(value: str, arg: str = ",") -> list[str]:
    """Split a string by the given separator."""
    if not value:
        return []
    return [item.strip() for item in value.split(arg)]


@register.filter
def format_amount(value: str) -> str:
    """
    Format ingredient amount by removing trailing zeros.

    - If amount is 0.0 or empty, return empty string
    - If amount ends with .0, return as whole number
    - Otherwise return as is
    """
    if not value or value.strip() == "":
        return ""

    try:
        # Try to convert to float
        num = float(value)

        # If it's zero, don't display it
        if num == 0.0:
            return ""

        # If it's a whole number (ends with .0), return without decimal
        if num == int(num):
            return str(int(num))

        # Otherwise return the original value to preserve fractions like "1/2"
        return value
    except (ValueError, TypeError):
        # Not a number, return as is (e.g., fractions like "1/2")
        return value
