"""Service for meal plan operations like shopping list aggregation and PDF data preparation."""

from __future__ import annotations

import logging
from collections import defaultdict
from fractions import Fraction
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models import MealPlan

logger = logging.getLogger(__name__)


def aggregate_shopping_list(meal_plan: MealPlan) -> list[tuple[str, str]]:
    """
    Aggregate ingredients from all recipes in a meal plan.

    Combines ingredients with the same name and unit, aggregating numeric amounts
    and collecting non-numeric amounts separately.

    Args:
        meal_plan: MealPlan instance with prefetched entries and recipe ingredients

    Returns:
        List of tuples (ingredient_name, display_amount) sorted alphabetically by name.
        The display_amount may contain multiple amounts with different units separated by commas.

    Example:
        [("flour", "2.5 cups"), ("salt", "1 tsp, to taste")]
    """
    logger.debug(f"Aggregating shopping list for meal plan '{meal_plan.name}' (ID: {meal_plan.pk})")

    # Aggregate ingredients by name and unit
    # ingredients_dict[name][unit] = total_amount (float)
    ingredients_dict: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    # Store non-numeric amounts separately
    # ingredients_non_numeric[name] = [display_strings]
    ingredients_non_numeric: dict[str, list[str]] = defaultdict(list)

    for entry in meal_plan.entries.all():
        recipe = entry.recipe
        servings_multiplier = entry.servings / recipe.servings if recipe.servings > 0 else 1

        for ingredient in recipe.ingredients.all():
            key = ingredient.name.lower()
            unit = ingredient.unit.strip() if ingredient.unit else ""

            # Try to parse and aggregate amounts
            if ingredient.amount:
                amount_str = ingredient.amount.strip()
                try:
                    # Try to parse as fraction or decimal
                    amount_value = float(Fraction(amount_str)) * servings_multiplier
                    ingredients_dict[key][unit] += amount_value
                except (ValueError, ZeroDivisionError):
                    # If can't parse, store as non-numeric
                    display = f"{amount_str} {unit}" if unit else amount_str
                    if display not in ingredients_non_numeric[key]:
                        ingredients_non_numeric[key].append(display)
            else:
                # No amount specified
                if unit:
                    display = unit
                    if display not in ingredients_non_numeric[key]:
                        ingredients_non_numeric[key].append(display)

    # Build formatted ingredient list
    ingredients_list: list[tuple[str, str]] = []
    for name in sorted(set(ingredients_dict.keys()) | set(ingredients_non_numeric.keys())):
        parts = []

        # Add numeric amounts grouped by unit
        if name in ingredients_dict:
            for unit in sorted(ingredients_dict[name].keys()):
                total = ingredients_dict[name][unit]
                # Format number nicely
                if total == int(total):
                    amount_str = str(int(total))
                else:
                    # Show up to 2 decimal places, remove trailing zeros
                    amount_str = f"{total:.2f}".rstrip("0").rstrip(".")

                if unit:
                    parts.append(f"{amount_str} {unit}")
                else:
                    parts.append(amount_str)

        # Add non-numeric amounts
        if name in ingredients_non_numeric:
            parts.extend(ingredients_non_numeric[name])

        display_value = ", ".join(parts) if parts else ""
        ingredients_list.append((name, display_value))

    logger.debug(f"Shopping list aggregated: {len(ingredients_list)} unique ingredients")
    return ingredients_list


def prepare_meal_plan_pdf_data(meal_plan: MealPlan) -> dict[str, Any]:
    """
    Prepare meal plan data structure for PDF generation.

    Args:
        meal_plan: MealPlan instance with prefetched entries, recipes, ingredients, and steps

    Returns:
        Dictionary with meal plan data formatted for Typst PDF template
    """
    logger.debug(f"Preparing PDF data for meal plan '{meal_plan.name}' (ID: {meal_plan.pk})")

    # Serialize meal plan data
    entries_data = []
    for entry in meal_plan.entries.all():
        prep_time_mins = int(entry.recipe.prep_time.total_seconds() / 60) if entry.recipe.prep_time else 0
        wait_time_mins = int(entry.recipe.wait_time.total_seconds() / 60) if entry.recipe.wait_time else 0

        entries_data.append(
            {
                "date": str(entry.date),
                "meal_type": entry.meal_type,
                "recipe_title": entry.recipe.title,
                "servings": entry.servings,
                "notes": entry.notes,
                "prep_time_minutes": prep_time_mins,
                "wait_time_minutes": wait_time_mins,
            }
        )

    meal_plan_data = {
        "name": meal_plan.name,
        "description": meal_plan.description,
        "start_date": str(meal_plan.start_date),
        "end_date": str(meal_plan.end_date),
        "entries": entries_data,
    }

    logger.debug(f"Meal plan PDF data prepared with {len(entries_data)} entries")
    return meal_plan_data


def prepare_shopping_list_pdf_data(meal_plan: MealPlan) -> dict[str, Any]:
    """
    Prepare shopping list data structure for PDF generation.

    Args:
        meal_plan: MealPlan instance with prefetched entries and recipe ingredients

    Returns:
        Dictionary with shopping list data formatted for Typst PDF template
    """
    logger.debug(f"Preparing shopping list PDF data for meal plan '{meal_plan.name}' (ID: {meal_plan.pk})")

    # Aggregate ingredients by name
    ingredients_dict: dict[str, dict[str, Any]] = defaultdict(lambda: {"items": [], "total_amount": ""})

    for entry in meal_plan.entries.all():
        recipe = entry.recipe

        for ingredient in recipe.ingredients.all():
            key = ingredient.name.lower()
            ingredients_dict[key]["items"].append(
                {
                    "amount": ingredient.amount,
                    "unit": ingredient.unit,
                    "recipe": recipe.title,
                }
            )

    # Sort ingredients alphabetically
    sorted_ingredients = []
    for name, data in sorted(ingredients_dict.items()):
        sorted_ingredients.append(
            {
                "name": name.title(),
                "items": data["items"],
                "total_amount": data.get("total_amount", ""),
            }
        )

    # Count unique recipes
    recipe_ids = set(entry.recipe_id for entry in meal_plan.entries.all())

    shopping_list_data = {
        "meal_plan_name": meal_plan.name,
        "start_date": str(meal_plan.start_date),
        "end_date": str(meal_plan.end_date),
        "ingredients": sorted_ingredients,
        "recipe_count": len(recipe_ids),
    }

    logger.debug(f"Shopping list PDF data prepared with {len(sorted_ingredients)} unique ingredients")
    return shopping_list_data
