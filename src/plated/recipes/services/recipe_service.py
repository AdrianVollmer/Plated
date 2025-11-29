"""Service for recipe operations like PDF generation, search, and filtering."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

if TYPE_CHECKING:
    from ..models import Recipe

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    """Exception raised when PDF generation fails."""

    pass


def search_recipes(queryset: models.QuerySet[Recipe], query: str | None) -> models.QuerySet[Recipe]:
    """
    Filter recipes by search query.

    Args:
        queryset: Base queryset to filter
        query: Search query string

    Returns:
        Filtered queryset
    """
    if not query:
        return queryset

    logger.info(f"Recipe search performed with query: '{query}'")
    filtered = queryset.filter(title__icontains=query) | queryset.filter(keywords__icontains=query)
    logger.debug(f"Search returned {filtered.count()} results")
    return filtered


def get_recipes_for_autocomplete() -> list[dict[str, int | str]]:
    """
    Get all recipes formatted for autocomplete.

    Returns:
        List of dicts with 'id' and 'title' keys
    """
    from ..models import Recipe

    recipes = Recipe.objects.all().order_by("title")
    return [{"id": recipe.pk, "title": recipe.title} for recipe in recipes]


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for use
    """
    safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in filename)
    return safe_name.replace(" ", "_")


def get_typst_translations(servings: int = 1) -> dict[str, str]:
    """
    Get translations for Typst template strings.

    Args:
        servings: Number of servings for proper pluralization

    Returns:
        Dictionary of translated strings for use in Typst templates
    """
    return {
        "ingredients": _("Ingredients"),
        "preparation": _("Preparation"),
        "chefs_tips": _("Chef's Tips"),
        "pairing_suggestions": _("Pairing Suggestions"),
        "servings": ngettext("serving", "servings", servings),
        "prep_time_label": _("Preparation:"),
        "wait_time_label": _("Waiting:"),
    }


def generate_recipe_pdf(recipe: Recipe, language: str = "en") -> bytes:
    """
    Generate a PDF for a recipe using Typst.

    Args:
        recipe: Recipe instance to generate PDF for
        language: Language code for translations (e.g., 'en', 'de')

    Returns:
        PDF content as bytes

    Raises:
        PDFGenerationError: If PDF generation fails for any reason
    """
    from django.utils import translation

    from ..schemas import serialize_recipe

    logger.info(f"PDF generation initiated for recipe: '{recipe.title}' (ID: {recipe.pk}) in language '{language}'")

    try:
        # Activate the specified language for translations
        with translation.override(language):
            # Get translations for Typst template
            translations = get_typst_translations(servings=recipe.servings)
            recipe_data = serialize_recipe(recipe)

            # Get the path to the Typst template
            base_dir = Path(__file__).resolve().parent.parent
            typst_template = base_dir / "typst" / "recipe.typ"

            if not typst_template.exists():
                error_msg = f"Typst template not found at {typst_template}"
                logger.error(error_msg)
                raise PDFGenerationError(error_msg)

            # Create temporary directory for intermediate files
            with tempfile.TemporaryDirectory(prefix="plated_typst_") as temp_dir:
                temp_path = Path(temp_dir)
                logger.debug(f"Using temporary directory: {temp_dir}")

                # Copy typst template to temp directory
                temp_typst = temp_path / "recipe.typ"
                shutil.copy(typst_template, temp_typst)

                # Write recipe JSON to temp directory (same location as typst file)
                recipe_json_path = temp_path / "recipe.json"
                with open(recipe_json_path, "w", encoding="utf-8") as f:
                    json.dump(recipe_data, f, indent=2, ensure_ascii=False)

                # Write translations JSON to temp directory
                translations_json_path = temp_path / "translations.json"
                with open(translations_json_path, "w", encoding="utf-8") as f:
                    json.dump(translations, f, indent=2, ensure_ascii=False)

                # Copy main image to temp directory if it exists
                image_filename = ""
                main_image = recipe.images.order_by("order").first()
                if main_image and main_image.image:
                    # Get the image file path
                    image_path = Path(main_image.image.path)
                    if image_path.exists():
                        # Use the original filename
                        image_filename = image_path.name
                        temp_image_path = temp_path / image_filename
                        shutil.copy(image_path, temp_image_path)
                        logger.debug(f"Copied main image to temp directory: {image_filename}")

                # Prepare output PDF path
                output_pdf = temp_path / "recipe.pdf"

                # Prepare Typst input data with relative paths
                typst_input_data = json.dumps(
                    {
                        "recipe": "recipe.json",
                        "translations": "translations.json",
                        "image": image_filename,
                    }
                )

                # Call Typst to compile the PDF
                try:
                    logger.debug(f"Running Typst compiler for recipe '{recipe.title}'")
                    # Run typst with trusted input only - recipe data is from database
                    subprocess.run(  # noqa: S603, S607
                        [  # noqa: S607
                            "typst",
                            "compile",
                            str(temp_typst),
                            str(output_pdf),
                            "--input",
                            f"data={typst_input_data}",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=True,
                    )
                except FileNotFoundError as e:
                    error_msg = "Typst executable not found on system"
                    logger.error(error_msg)
                    raise PDFGenerationError(error_msg) from e
                except subprocess.TimeoutExpired as e:
                    error_msg = f"Typst compilation timed out for recipe '{recipe.title}' (ID: {recipe.pk})"
                    logger.error(error_msg)
                    raise PDFGenerationError(error_msg) from e
                except subprocess.CalledProcessError as e:
                    error_msg = f"Typst compilation failed: {e.stderr if e.stderr else str(e)}"
                    logger.error(f"Typst compilation failed for recipe '{recipe.title}' (ID: {recipe.pk}): {e.stderr}")
                    raise PDFGenerationError(error_msg) from e

                # Check if PDF was created
                if not output_pdf.exists():
                    error_msg = "PDF file was not generated"
                    logger.error(f"PDF file not created for recipe '{recipe.title}' (ID: {recipe.pk})")
                    raise PDFGenerationError(error_msg)

                # Read the PDF file
                with open(output_pdf, "rb") as pdf_file:
                    pdf_content = pdf_file.read()

                logger.info(f"PDF generated successfully for recipe '{recipe.title}' (ID: {recipe.pk})")
                return pdf_content

    except PDFGenerationError:
        # Re-raise PDF generation errors as-is
        raise
    except Exception as e:
        error_msg = f"Unexpected error generating PDF: {e}"
        logger.error(f"Unexpected error generating PDF for recipe '{recipe.title}' (ID: {recipe.pk}): {e}")
        raise PDFGenerationError(error_msg) from e
