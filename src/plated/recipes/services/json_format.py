"""JSON format handler for recipe import/export."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ..schema import deserialize_recipe, serialize_recipe, validate_recipe_data
from .base import RecipeFormatHandler

if TYPE_CHECKING:
    from ..models import Recipe


class JSONFormatHandler(RecipeFormatHandler):
    """Handler for JSON format recipe import/export."""

    @property
    def format_name(self) -> str:
        """Human-readable name of the format."""
        return "JSON"

    @property
    def format_id(self) -> str:
        """Unique identifier for the format."""
        return "json"

    @property
    def file_extension(self) -> str:
        """File extension for this format."""
        return ".json"

    @property
    def mime_type(self) -> str:
        """MIME type for this format."""
        return "application/json"

    def can_import(self, content: str) -> bool:
        """
        Check if the content is valid JSON.

        Args:
            content: The file content as a string

        Returns:
            True if the content is valid JSON, False otherwise
        """
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False

    def import_recipe(self, content: str) -> Recipe:
        """
        Import a recipe from JSON content.

        Args:
            content: The JSON content as a string

        Returns:
            A fully saved Recipe model instance with all related objects

        Raises:
            ValueError: If the content is invalid or cannot be parsed
        """
        from django.db import transaction

        from ..models import Ingredient, Step

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        # Validate the data
        errors = validate_recipe_data(data)
        if errors:
            error_msg = "\n".join(errors)
            raise ValueError(f"Invalid recipe data:\n{error_msg}")

        # Deserialize to Recipe instance
        deserialized = deserialize_recipe(data)

        # Create the recipe and related objects in a transaction
        with transaction.atomic():
            recipe = Recipe.objects.create(**deserialized["recipe_data"])

            # Create ingredients
            for ing_data in deserialized["ingredients_data"]:
                Ingredient.objects.create(recipe=recipe, **ing_data)

            # Create steps
            for step_data in deserialized["steps_data"]:
                Step.objects.create(recipe=recipe, **step_data)

        return recipe

    def export_recipe(self, recipe: Recipe) -> str:
        """
        Export a recipe to JSON string.

        Args:
            recipe: The Recipe model instance to export

        Returns:
            The recipe data as a JSON string

        Raises:
            ValueError: If the recipe cannot be exported
        """
        try:
            recipe_data = serialize_recipe(recipe)
            return json.dumps(recipe_data, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ValueError(f"Error exporting recipe: {e}") from e
