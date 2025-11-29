"""Validation functions for recipe data."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_recipe_data(data: dict[str, Any]) -> list[str]:
    """
    Validate recipe data and return a list of error messages.

    Returns an empty list if the data is valid.
    """
    logger.debug("Validating recipe data")
    errors: list[str] = []

    # Check required fields
    if not data.get("title"):
        errors.append("Recipe must have a title")

    # Validate servings
    servings = data.get("servings", 1)
    if not isinstance(servings, int) or servings < 1:
        errors.append("Servings must be a positive integer")

    # Validate time fields
    if "prep_time_minutes" in data:
        prep_time = data["prep_time_minutes"]
        if prep_time is not None and (not isinstance(prep_time, int) or prep_time < 0):
            errors.append("prep_time_minutes must be a non-negative integer or null")

    if "wait_time_minutes" in data:
        wait_time = data["wait_time_minutes"]
        if wait_time is not None and (not isinstance(wait_time, int) or wait_time < 0):
            errors.append("wait_time_minutes must be a non-negative integer or null")

    # Validate ingredients
    ingredients = data.get("ingredients", [])
    if not isinstance(ingredients, list):
        errors.append("Ingredients must be a list")
    else:
        for i, ing in enumerate(ingredients):
            if not isinstance(ing, dict):
                errors.append(f"Ingredient {i + 1} must be an object")
                continue
            if not ing.get("name"):
                errors.append(f"Ingredient {i + 1} must have a name")

    # Validate steps
    steps = data.get("steps", [])
    if not isinstance(steps, list):
        errors.append("Steps must be a list")
    else:
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"Step {i + 1} must be an object")
                continue
            if not step.get("content"):
                errors.append(f"Step {i + 1} must have content")

    # Validate images
    images = data.get("images", [])
    if not isinstance(images, list):
        errors.append("Images must be a list")

    if errors:
        logger.warning(f"Recipe data validation failed with {len(errors)} errors")
    else:
        logger.debug("Recipe data validation passed")

    return errors
