"""Serialization and deserialization functions for recipe data."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from .types import ImageSchema, IngredientSchema, RecipeSchema, StepSchema

logger = logging.getLogger(__name__)


def serialize_recipe(recipe: Any) -> RecipeSchema:
    """Convert a Recipe model instance to a JSON-serializable dict."""
    logger.debug(f"Serializing recipe: '{recipe.title}' (ID: {recipe.pk})")

    try:
        data: RecipeSchema = {
            "title": recipe.title,
            "description": recipe.description,
            "servings": recipe.servings,
            "keywords": recipe.keywords,
            "url": recipe.url,
            "notes": recipe.notes,
            "special_equipment": recipe.special_equipment,
        }

        # Convert durations to minutes for easier editing
        if recipe.prep_time:
            data["prep_time_minutes"] = int(recipe.prep_time.total_seconds() / 60)
        else:
            data["prep_time_minutes"] = None

        if recipe.wait_time:
            data["wait_time_minutes"] = int(recipe.wait_time.total_seconds() / 60)
        else:
            data["wait_time_minutes"] = None

        # Serialize ingredients
        ingredients: list[IngredientSchema] = []
        for ingredient in recipe.ingredients.all():
            ing_data: IngredientSchema = {
                "name": ingredient.name,
                "order": ingredient.order,
            }
            if ingredient.amount:
                ing_data["amount"] = ingredient.amount
            if ingredient.unit:
                ing_data["unit"] = ingredient.unit
            if ingredient.note:
                ing_data["note"] = ingredient.note
            ingredients.append(ing_data)
        data["ingredients"] = ingredients

        # Serialize steps
        steps: list[StepSchema] = [{"content": step.content, "order": step.order} for step in recipe.steps.all()]
        data["steps"] = steps

        # Serialize image metadata (not the actual files)
        images: list[ImageSchema] = []
        for image in recipe.images.all():
            img_data: ImageSchema = {"order": image.order}
            if image.caption:
                img_data["caption"] = image.caption
            images.append(img_data)
        data["images"] = images

        logger.debug(
            f"Recipe serialized: '{recipe.title}' with {len(ingredients)} ingredients, "
            f"{len(steps)} steps, {len(images)} images"
        )
        return data
    except Exception as e:
        logger.error(
            f"Error serializing recipe '{recipe.title}' (ID: {recipe.pk}): {e}",
            exc_info=True,
        )
        raise


def deserialize_recipe(data: dict[str, Any]) -> dict[str, Any]:
    """
    Convert JSON data to a format suitable for creating a Recipe model.

    Returns a dict with 'recipe_data', 'ingredients_data', 'steps_data',
    and 'images_data'.
    """
    title = data.get("title", "")
    logger.debug(f"Deserializing recipe data for: '{title}'")

    try:
        recipe_data = {
            "title": title,
            "description": data.get("description", ""),
            "servings": data.get("servings", 1),
            "keywords": data.get("keywords", ""),
            "url": data.get("url", ""),
            "notes": data.get("notes", ""),
            "special_equipment": data.get("special_equipment", ""),
        }

        # Convert minutes to timedelta
        if data.get("prep_time_minutes") is not None:
            recipe_data["prep_time"] = timedelta(minutes=data["prep_time_minutes"])
        else:
            recipe_data["prep_time"] = None

        if data.get("wait_time_minutes") is not None:
            recipe_data["wait_time"] = timedelta(minutes=data["wait_time_minutes"])
        else:
            recipe_data["wait_time"] = None

        # Extract related data
        ingredients_data = data.get("ingredients", [])
        steps_data = data.get("steps", [])
        images_data = data.get("images", [])

        logger.debug(
            f"Recipe deserialized: '{title}' with {len(ingredients_data)} ingredients, {len(steps_data)} steps"
        )

        return {
            "recipe_data": recipe_data,
            "ingredients_data": ingredients_data,
            "steps_data": steps_data,
            "images_data": images_data,
        }
    except Exception as e:
        logger.error(f"Error deserializing recipe data for '{title}': {e}", exc_info=True)
        raise
