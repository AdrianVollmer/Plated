"""Service for managing ingredient properties (names, units, keywords)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.db import models as django_models
from django.db import transaction

if TYPE_CHECKING:
    from ..models import Recipe

logger = logging.getLogger(__name__)


def parse_keywords(keywords_str: str) -> list[str]:
    """
    Parse a comma-separated keyword string into a list of cleaned keywords.

    Args:
        keywords_str: Comma-separated string of keywords

    Returns:
        List of cleaned, non-empty keywords
    """
    return [kw.strip() for kw in keywords_str.split(",") if kw.strip()]


def get_all_recipe_keywords() -> list[str]:
    """
    Get all distinct keywords from recipes as a flat list.

    Returns:
        List of all keyword strings (comma-separated) from recipes
    """
    from ..models import Recipe

    return list(Recipe.objects.exclude(keywords="").values_list("keywords", flat=True))


def get_ingredient_property_with_counts(
    field_name: str,
    exclude_empty: bool = False,
    search_query: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get distinct ingredient property values with usage counts.

    Args:
        field_name: Field name on Ingredient model ('name' or 'unit')
        exclude_empty: Whether to exclude empty values
        search_query: Optional search query to filter results

    Returns:
        List of dicts with field_name and 'usage_count' keys
    """
    from ..models import Ingredient

    queryset = (
        Ingredient.objects.values(field_name).annotate(usage_count=django_models.Count("id")).order_by(field_name)
    )

    if exclude_empty:
        queryset = queryset.exclude(**{field_name: ""})

    if search_query:
        queryset = queryset.filter(**{f"{field_name}__icontains": search_query})

    return list(queryset)


def get_keywords_with_counts(search_query: str | None = None) -> list[dict[str, Any]]:
    """
    Get all keywords with their usage counts.

    Args:
        search_query: Optional search query to filter results

    Returns:
        List of dicts with 'keyword' and 'usage_count' keys, sorted alphabetically
    """
    keyword_counts: dict[str, int] = {}
    for keywords_str in get_all_recipe_keywords():
        for keyword in parse_keywords(keywords_str):
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

    # Convert to list of dicts and sort
    keywords: list[dict[str, Any]] = [{"keyword": k, "usage_count": v} for k, v in keyword_counts.items()]
    keywords.sort(key=lambda x: str(x["keyword"]).lower())

    # Apply search filter
    if search_query:
        keywords = [k for k in keywords if search_query.lower() in str(k["keyword"]).lower()]

    return keywords


def get_ingredient_names_for_autocomplete() -> list[str]:
    """
    Get all distinct ingredient names for autocomplete.

    Returns:
        Sorted list of ingredient names
    """
    from ..models import Ingredient

    return list(Ingredient.objects.values_list("name", flat=True).distinct().order_by("name"))


def get_units_for_autocomplete() -> list[str]:
    """
    Get all distinct units for autocomplete.

    Returns:
        Sorted list of units (excluding empty strings)
    """
    from ..models import Ingredient

    return list(Ingredient.objects.exclude(unit="").values_list("unit", flat=True).distinct().order_by("unit"))


def get_keywords_for_autocomplete() -> list[str]:
    """
    Get all distinct keywords for autocomplete.

    Returns:
        Sorted list of keywords
    """
    keywords_set = set()
    for keywords_str in get_all_recipe_keywords():
        keywords_set.update(parse_keywords(keywords_str))

    return sorted(keywords_set, key=str.lower)


def rename_ingredient_property(
    field_name: str,
    old_value: str,
    new_value: str,
) -> int:
    """
    Rename an ingredient property across all recipes.

    Args:
        field_name: Field name on Ingredient model ('name' or 'unit')
        old_value: Current value to rename
        new_value: New value to set

    Returns:
        Number of ingredient instances updated

    Raises:
        ValueError: If old_value doesn't exist or values are the same
    """
    from ..models import Ingredient

    if not old_value:
        raise ValueError("Old value is required")

    if old_value == new_value:
        raise ValueError("Old and new values are the same")

    # Check if old value exists
    count = Ingredient.objects.filter(**{field_name: old_value}).count()
    if count == 0:
        raise ValueError(f"No ingredients found with {field_name} '{old_value}'")

    # Update all ingredients with the old value
    with transaction.atomic():
        updated = Ingredient.objects.filter(**{field_name: old_value}).update(**{field_name: new_value})

    logger.info(f"Ingredient {field_name} renamed: '{old_value}' -> '{new_value}' ({updated} occurrences)")
    return updated


def rename_keyword(old_keyword: str, new_keyword: str) -> int:
    """
    Rename a keyword across all recipes.

    Args:
        old_keyword: Current keyword to rename
        new_keyword: New keyword value

    Returns:
        Number of recipes updated

    Raises:
        ValueError: If old_keyword doesn't exist or keywords are the same
    """
    from ..models import Recipe

    if not old_keyword:
        raise ValueError("Old keyword is required")

    if not new_keyword:
        raise ValueError("New keyword is required")

    if old_keyword == new_keyword:
        raise ValueError("Old and new keywords are the same")

    # Find all recipes with the old keyword
    recipes_to_update = [
        recipe for recipe in Recipe.objects.exclude(keywords="") if old_keyword in parse_keywords(recipe.keywords)
    ]

    if not recipes_to_update:
        raise ValueError(f"No recipes found with keyword '{old_keyword}'")

    # Update keywords in all matching recipes
    with transaction.atomic():
        updated_count = 0
        for recipe in recipes_to_update:
            keywords_list = parse_keywords(recipe.keywords)
            # Replace old keyword with new keyword
            keywords_list = [new_keyword if kw == old_keyword else kw for kw in keywords_list]
            # Deduplicate while preserving order
            seen = set()
            deduplicated = []
            for kw in keywords_list:
                if kw not in seen:
                    seen.add(kw)
                    deduplicated.append(kw)
            # Update the recipe
            recipe.keywords = ", ".join(deduplicated)
            recipe.save()
            updated_count += 1

    logger.info(f"Keyword renamed: '{old_keyword}' -> '{new_keyword}' ({updated_count} recipes updated)")
    return updated_count


def get_usage_count(field_name: str, value: str) -> int:
    """
    Get usage count for an ingredient property value.

    Args:
        field_name: Field name on Ingredient model ('name' or 'unit')
        value: Property value to count

    Returns:
        Number of ingredients using this value
    """
    from ..models import Ingredient

    return Ingredient.objects.filter(**{field_name: value}).count()


def get_keyword_usage_count(keyword: str) -> int:
    """
    Get usage count for a keyword.

    Args:
        keyword: Keyword to count

    Returns:
        Number of recipes using this keyword
    """
    return sum(1 for keywords_str in get_all_recipe_keywords() if keyword in parse_keywords(keywords_str))


def get_recipes_by_ingredient_name(name: str) -> list[Recipe]:
    """
    Get all recipes that use a specific ingredient name.

    Args:
        name: Ingredient name to filter by

    Returns:
        List of Recipe instances
    """
    from ..models import Recipe

    return list(Recipe.objects.filter(ingredients__name=name).distinct())


def get_recipes_by_unit(unit: str) -> list[Recipe]:
    """
    Get all recipes that use a specific unit.

    Args:
        unit: Unit to filter by

    Returns:
        List of Recipe instances
    """
    from ..models import Recipe

    return list(Recipe.objects.filter(ingredients__unit=unit).distinct())


def get_recipes_by_keyword(keyword: str) -> list[Recipe]:
    """
    Get all recipes that use a specific keyword.

    Args:
        keyword: Keyword to filter by

    Returns:
        List of Recipe instances with exact keyword match
    """
    from ..models import Recipe

    recipes = Recipe.objects.filter(keywords__icontains=keyword).distinct()
    # Further filter to ensure exact keyword match (not just substring)
    return [recipe for recipe in recipes if keyword in parse_keywords(recipe.keywords)]
