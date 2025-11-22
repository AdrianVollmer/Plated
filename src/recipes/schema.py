"""JSON schema for recipe import/export."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, TypedDict

logger = logging.getLogger(__name__)


class IngredientSchema(TypedDict, total=False):
    """Schema for an ingredient."""

    amount: str
    unit: str
    name: str
    note: str
    order: int


class StepSchema(TypedDict):
    """Schema for a recipe step."""

    content: str
    order: int


class ImageSchema(TypedDict, total=False):
    """Schema for a recipe image metadata (not the actual image file)."""

    caption: str
    order: int


class RecipeSchema(TypedDict, total=False):
    """Schema for a complete recipe."""

    title: str
    description: str
    servings: int
    keywords: str
    prep_time_minutes: int | None
    wait_time_minutes: int | None
    url: str
    notes: str
    special_equipment: str
    ingredients: list[IngredientSchema]
    steps: list[StepSchema]
    images: list[ImageSchema]


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


def get_recipe_json_schema() -> dict[str, Any]:
    """
    Generate a JSON schema example for recipe extraction by AI.

    Returns a dictionary with example values that demonstrates the expected
    structure for recipe data. This is used to guide AI models in extracting
    recipe information.
    """
    return {
        "title": "Recipe title (required)",
        "description": "Brief description",
        "servings": 4,
        "keywords": "comma, separated, keywords",
        "prep_time_minutes": 30,
        "wait_time_minutes": 45,
        "url": "source URL if applicable",
        "notes": "any additional notes",
        "special_equipment": "special equipment needed",
        "ingredients": [
            {
                "amount": "2",
                "unit": "cups",
                "name": "flour",
                "note": "sifted",
                "order": 0,
            }
        ],
        "steps": [
            {
                "content": "Step instructions (markdown supported)",
                "order": 0,
            }
        ],
    }


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
