"""Mock format handlers for demonstration purposes.

These are simplified examples to demonstrate the format handler pattern.
They are not meant for production use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import Ingredient, Recipe, Step
from .base import RecipeFormatHandler

if TYPE_CHECKING:
    pass


class SimpleTextFormatHandler(RecipeFormatHandler):
    """
    Mock handler for a simple text format.

    Format example:
    TITLE: My Recipe
    SERVINGS: 4
    DESCRIPTION: A delicious recipe

    INGREDIENTS:
    - 2 cups flour
    - 1 tsp salt

    STEPS:
    1. Mix ingredients
    2. Bake at 350F
    """

    @property
    def format_name(self) -> str:
        """Human-readable name of the format."""
        return "Simple Text (Demo)"

    @property
    def format_id(self) -> str:
        """Unique identifier for the format."""
        return "simple_text"

    @property
    def file_extension(self) -> str:
        """File extension for this format."""
        return ".txt"

    @property
    def mime_type(self) -> str:
        """MIME type for this format."""
        return "text/plain"

    def can_import(self, content: str) -> bool:
        """Check if content looks like our simple text format."""
        return "TITLE:" in content and ("INGREDIENTS:" in content or "STEPS:" in content)

    def import_recipe(self, content: str) -> Recipe:
        """
        Import a recipe from simple text format.

        This is a mock implementation for demonstration.
        """
        lines = content.strip().split("\n")
        recipe_data: dict[str, str | int] = {}
        ingredients: list[str] = []
        steps: list[str] = []
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("TITLE:"):
                recipe_data["title"] = line.replace("TITLE:", "").strip()
            elif line.startswith("SERVINGS:"):
                try:
                    recipe_data["servings"] = int(line.replace("SERVINGS:", "").strip())
                except ValueError:
                    recipe_data["servings"] = 1
            elif line.startswith("DESCRIPTION:"):
                recipe_data["description"] = line.replace("DESCRIPTION:", "").strip()
            elif line == "INGREDIENTS:":
                current_section = "ingredients"
            elif line == "STEPS:":
                current_section = "steps"
            elif current_section == "ingredients" and line.startswith("-"):
                ingredients.append(line[1:].strip())
            elif current_section == "steps" and line[0].isdigit():
                steps.append(line.split(".", 1)[1].strip() if "." in line else line)

        if "title" not in recipe_data:
            raise ValueError("Missing required field: TITLE")

        # Create recipe instance
        recipe = Recipe(
            title=str(recipe_data.get("title", "Untitled")),
            description=str(recipe_data.get("description", "")),
            servings=int(recipe_data.get("servings", 1)),
        )

        # Note: In a real implementation, we would properly handle ingredients and steps
        # For now, we just demonstrate the pattern
        return recipe

    def export_recipe(self, recipe: Recipe) -> str:
        """Export a recipe to simple text format."""
        lines = [
            f"TITLE: {recipe.title}",
            f"SERVINGS: {recipe.servings}",
            f"DESCRIPTION: {recipe.description}",
            "",
            "INGREDIENTS:",
        ]

        for ingredient in recipe.ingredients.all():
            lines.append(f"- {ingredient}")

        lines.extend(["", "STEPS:"])

        for idx, step in enumerate(recipe.steps.all(), 1):
            lines.append(f"{idx}. {step.content}")

        return "\n".join(lines)


class CSVLikeFormatHandler(RecipeFormatHandler):
    """
    Mock handler for a CSV-like format.

    This is a simplified demonstration format where recipe metadata
    is stored in a CSV-like structure.
    """

    @property
    def format_name(self) -> str:
        """Human-readable name of the format."""
        return "CSV-Like (Demo)"

    @property
    def format_id(self) -> str:
        """Unique identifier for the format."""
        return "csv_like"

    @property
    def file_extension(self) -> str:
        """File extension for this format."""
        return ".csv"

    @property
    def mime_type(self) -> str:
        """MIME type for this format."""
        return "text/csv"

    def can_import(self, content: str) -> bool:
        """Check if content looks like CSV format."""
        # Very simple check - just see if it has commas
        lines = content.strip().split("\n")
        return len(lines) > 0 and "," in lines[0]

    def import_recipe(self, content: str) -> Recipe:
        """
        Import a recipe from CSV-like format.

        This is a mock implementation for demonstration.
        Format: title,servings,description
        """
        lines = content.strip().split("\n")
        if not lines:
            raise ValueError("Empty content")

        # Simple parsing - first line is data
        parts = lines[0].split(",")
        if len(parts) < 2:
            raise ValueError("Invalid CSV format")

        recipe = Recipe(
            title=parts[0].strip(),
            servings=int(parts[1].strip()) if len(parts) > 1 else 1,
            description=parts[2].strip() if len(parts) > 2 else "",
        )

        return recipe

    def export_recipe(self, recipe: Recipe) -> str:
        """Export a recipe to CSV-like format."""
        # Simple CSV with title, servings, description
        description = recipe.description.replace(",", ";")  # Escape commas
        return f"{recipe.title},{recipe.servings},{description}"
