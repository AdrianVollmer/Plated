"""Tandoor format handler for recipe import."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .base import RecipeFormatHandler

if TYPE_CHECKING:
    from ..models import Recipe


class TandoorFormatHandler(RecipeFormatHandler):
    """Handler for Tandoor recipe format import."""

    @property
    def format_name(self) -> str:
        """Human-readable name of the format."""
        return "Tandoor"

    @property
    def format_id(self) -> str:
        """Unique identifier for the format."""
        return "tandoor"

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
        Check if the content is valid Tandoor JSON.

        Args:
            content: The file content as a string

        Returns:
            True if the content appears to be Tandoor format, False otherwise
        """
        try:
            data = json.loads(content)
            # Check for Tandoor-specific fields
            return isinstance(data, dict) and "name" in data and "steps" in data
        except json.JSONDecodeError:
            return False

    def _extract_ingredients_from_steps(self, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Extract and flatten ingredients from Tandoor steps structure.

        Args:
            steps: List of step dictionaries from Tandoor format

        Returns:
            List of ingredient dictionaries in Plated format
        """
        ingredients: list[dict[str, Any]] = []
        order = 0

        for step in steps:
            step_ingredients = step.get("ingredients", [])
            for ing in step_ingredients:
                food = ing.get("food", {})
                unit = ing.get("unit", {})
                amount = ing.get("amount")
                note = ing.get("note", "")

                ingredient_data: dict[str, Any] = {
                    "name": food.get("name", ""),
                    "order": order,
                }

                if amount is not None:
                    # Convert amount to string since Ingredient.amount is CharField
                    ingredient_data["amount"] = str(amount)

                if unit and unit.get("name"):
                    ingredient_data["unit"] = unit["name"]

                if note:
                    ingredient_data["note"] = note

                ingredients.append(ingredient_data)
                order += 1

        return ingredients

    def _extract_steps(self, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Extract steps from Tandoor format.

        Args:
            steps: List of step dictionaries from Tandoor format

        Returns:
            List of step dictionaries in Plated format
        """
        plated_steps: list[dict[str, Any]] = []

        for idx, step in enumerate(steps):
            instruction = step.get("instruction", "").strip()
            if instruction:
                plated_steps.append({"content": instruction, "order": idx})

        return plated_steps

    def _extract_keywords(self, keywords: list[dict[str, Any]]) -> str:
        """
        Extract keywords from Tandoor format.

        Args:
            keywords: List of keyword dictionaries from Tandoor format

        Returns:
            Comma-separated string of keywords
        """
        keyword_names = [kw.get("name", "") for kw in keywords if kw.get("name")]
        return ", ".join(keyword_names)

    def import_recipe(self, content: str) -> Recipe:
        """
        Import a recipe from Tandoor JSON content.

        Args:
            content: The Tandoor JSON content as a string

        Returns:
            A fully saved Recipe model instance with all related objects

        Raises:
            ValueError: If the content is invalid or cannot be parsed
        """
        from django.db import transaction

        from ..models import Ingredient, Recipe, Step

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        # Validate basic structure
        if not isinstance(data, dict):
            raise ValueError("Invalid Tandoor format: expected object")

        if "name" not in data:
            raise ValueError("Invalid Tandoor format: missing 'name' field")

        # Extract recipe data
        title = data.get("name", "Untitled Recipe")
        description = data.get("description", "")
        servings = data.get("servings", 1)
        source_url = data.get("source_url", "")

        # Convert times from minutes to timedelta
        prep_time = None
        wait_time = None

        working_time = data.get("working_time")
        if working_time:
            from datetime import timedelta

            prep_time = timedelta(minutes=working_time)

        waiting_time = data.get("waiting_time")
        if waiting_time:
            from datetime import timedelta

            wait_time = timedelta(minutes=waiting_time)

        # Extract keywords
        keywords = ""
        if data.get("keywords"):
            keywords = self._extract_keywords(data["keywords"])

        # Extract ingredients and steps
        steps_data = data.get("steps", [])
        ingredients = self._extract_ingredients_from_steps(steps_data)
        steps = self._extract_steps(steps_data)

        # Create the recipe and related objects in a transaction
        with transaction.atomic():
            recipe = Recipe.objects.create(
                title=title,
                description=description,
                servings=servings,
                keywords=keywords,
                prep_time=prep_time,
                wait_time=wait_time,
                url=source_url,
            )

            # Create ingredients
            for ing_data in ingredients:
                Ingredient.objects.create(recipe=recipe, **ing_data)

            # Create steps
            for step_data in steps:
                Step.objects.create(recipe=recipe, **step_data)

        return recipe

    def export_recipe(self, recipe: Recipe) -> str:
        """
        Export a recipe to Tandoor format.

        Note: This is not fully implemented as export to Tandoor format
        is not a primary requirement. Returns JSON error message.

        Args:
            recipe: The Recipe model instance to export

        Returns:
            Error message

        Raises:
            NotImplementedError: Always, as Tandoor export is not supported
        """
        raise NotImplementedError("Export to Tandoor format is not supported")
