from __future__ import annotations

import datetime

from django import template

register = template.Library()


@register.filter
def format_duration(value: datetime.timedelta | None) -> str:
    """Format a timedelta into a human-readable string.

    Examples:
        None or zero  -> ""
        45 seconds    -> "45 sec"
        13 minutes    -> "13 min"
        90 minutes    -> "1 hr 30 min"
        120 minutes   -> "2 hr"
    """
    if not value:
        return ""
    total_seconds = int(value.total_seconds())
    if total_seconds <= 0:
        return ""
    if total_seconds < 60:
        unit = "sec" if total_seconds == 1 else "sec"
        return f"{total_seconds} {unit}"
    total_minutes = total_seconds // 60
    if total_minutes < 60:
        return f"{total_minutes} min"
    hours, minutes = divmod(total_minutes, 60)
    hr_label = "hr"
    if minutes == 0:
        return f"{hours} {hr_label}"
    return f"{hours} {hr_label} {minutes} min"


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
