from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def split(value: str, arg: str = ",") -> list[str]:
    """Split a string by the given separator."""
    if not value:
        return []
    return [item.strip() for item in value.split(arg)]
