from __future__ import annotations

import logging

from django.conf import settings as django_settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.translation import gettext as _

from ..forms import AISettingsForm, DatabaseImportForm, UserSettingsForm
from ..middleware import LANGUAGE_SESSION_KEY
from ..models import AISettings, UserSettings
from ..services import (
    ExportError,
    export_json_database,
    export_sql_dump,
    export_sqlite_database,
    get_available_export_formats,
    get_export_filename,
)

logger = logging.getLogger(__name__)


def settings_view(request: HttpRequest) -> HttpResponse:
    """Display application settings page."""
    # Ensure session exists
    if not request.session.session_key:
        request.session.create()

    # Get or create user settings based on session key
    user_settings, created = UserSettings.objects.get_or_create(
        session_key=request.session.session_key,
        defaults={"language": translation.get_language() or "en"},
    )

    # Get AI settings (singleton)
    ai_settings = AISettings.objects.first()

    if request.method == "POST":
        # Handle user settings form submission
        if "user_settings" in request.POST:
            user_form = UserSettingsForm(request.POST, instance=user_settings)
            if user_form.is_valid():
                user_form.save()
                # Activate the new language immediately
                language = user_form.cleaned_data["language"]
                translation.activate(language)
                request.session[LANGUAGE_SESSION_KEY] = language
                messages.success(request, _("Language settings saved successfully!"))
                logger.info(f"Language settings updated to {language}")
                # Set language cookie to persist across requests
                response = redirect("settings")
                response.set_cookie(django_settings.LANGUAGE_COOKIE_NAME, language)
                return response
        # Handle AI settings form submission
        elif "ai_settings" in request.POST:
            if ai_settings:
                ai_form = AISettingsForm(request.POST, instance=ai_settings)
            else:
                ai_form = AISettingsForm(request.POST)

            if ai_form.is_valid():
                ai_form.save()
                messages.success(request, _("AI settings saved successfully!"))
                logger.info("AI settings updated")
                return redirect("settings")

    # Initialize forms for GET request
    user_form = UserSettingsForm(instance=user_settings)
    ai_form = AISettingsForm(instance=ai_settings) if ai_settings else AISettingsForm()

    # Get available export formats
    export_formats = get_available_export_formats()

    # Initialize import form
    import_form = DatabaseImportForm()

    return render(
        request,
        "recipes/settings.html",
        {
            "user_settings": user_settings,
            "user_form": user_form,
            "ai_settings": ai_settings,
            "ai_form": ai_form,
            "export_formats": export_formats,
            "import_form": import_form,
        },
    )


def export_database(request: HttpRequest, format_type: str) -> HttpResponse:
    """Export the database in the specified format."""
    logger.info(f"Database export requested: format={format_type}")

    try:
        # Get the export function and content type based on format
        content: bytes | str
        if format_type == "sqlite":
            content = export_sqlite_database()
            content_type = "application/x-sqlite3"
        elif format_type == "json":
            content = export_json_database()
            content_type = "application/json"
        elif format_type == "sql":
            content = export_sql_dump()
            content_type = "text/plain"
        else:
            logger.warning(f"Invalid export format requested: {format_type}")
            messages.error(request, _("Invalid export format"))
            return redirect("settings")

        # Create the response
        response = HttpResponse(content, content_type=content_type)
        filename = get_export_filename(format_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        logger.info(f"Database export successful: format={format_type}, filename={filename}")
        return response

    except ExportError as e:
        logger.error(f"Export failed: {e}")
        messages.error(request, _("Export failed: %(error)s") % {"error": str(e)})
        return redirect("settings")
    except Exception as e:
        logger.error(f"Unexpected error during export: {e}", exc_info=True)
        messages.error(request, _("An unexpected error occurred during export"))
        return redirect("settings")


def import_database_upload(request: HttpRequest) -> HttpResponse:
    """Handle database import file upload."""
    if request.method != "POST":
        return redirect("settings")

    form = DatabaseImportForm(request.POST, request.FILES)

    if not form.is_valid():
        for error_list in form.errors.values():
            for error in error_list:
                messages.error(request, str(error))
        return redirect("settings")

    import_format = form.cleaned_data["format"]
    import_file = form.cleaned_data["import_file"]

    logger.info(f"Database import upload: format={import_format}, filename={import_file.name}")

    try:
        import base64
        import json
        import zipfile
        from io import BytesIO

        # Read the uploaded file
        file_content = import_file.read()

        # Parse recipes based on format
        recipes_data: list[dict] = []

        if import_format == "tandoor":
            # Tandoor format: main zip contains multiple recipe zips
            try:
                main_zip = zipfile.ZipFile(BytesIO(file_content))
                recipe_zips = [name for name in main_zip.namelist() if name.endswith(".zip")]

                for recipe_zip_name in recipe_zips:
                    try:
                        # Extract the inner zip
                        recipe_zip_bytes = main_zip.read(recipe_zip_name)
                        recipe_zip = zipfile.ZipFile(BytesIO(recipe_zip_bytes))

                        # Look for recipe.json
                        if "recipe.json" in recipe_zip.namelist():
                            recipe_json = recipe_zip.read("recipe.json").decode("utf-8")
                            recipe_data = json.loads(recipe_json)

                            # Store the image if present (encode as base64 for session storage)
                            image_data = None
                            if "image.jpg" in recipe_zip.namelist():
                                image_bytes = recipe_zip.read("image.jpg")
                                image_data = base64.b64encode(image_bytes).decode("utf-8")

                            recipes_data.append(
                                {"json": recipe_json, "image": image_data, "name": recipe_data.get("name", "Unknown")}
                            )
                    except Exception as e:
                        logger.warning(f"Failed to parse recipe zip {recipe_zip_name}: {e}")
                        continue

            except zipfile.BadZipFile:
                messages.error(request, _("Invalid zip file"))
                return redirect("settings")

        elif import_format == "plated":
            # Plated format: could be a single JSON file or zip with multiple JSONs
            try:
                # Try to parse as zip first
                main_zip = zipfile.ZipFile(BytesIO(file_content))
                json_files = [name for name in main_zip.namelist() if name.endswith(".json")]

                for json_file in json_files:
                    recipe_json = main_zip.read(json_file).decode("utf-8")
                    recipe_data = json.loads(recipe_json)
                    recipes_data.append(
                        {"json": recipe_json, "image": None, "name": recipe_data.get("title", "Unknown")}
                    )

            except zipfile.BadZipFile:
                # Not a zip, try as raw JSON
                try:
                    recipe_json = file_content.decode("utf-8")
                    recipe_data = json.loads(recipe_json)

                    # Check if it's an array of recipes or a single recipe
                    if isinstance(recipe_data, list):
                        for recipe in recipe_data:
                            recipes_data.append(
                                {"json": json.dumps(recipe), "image": None, "name": recipe.get("title", "Unknown")}
                            )
                    else:
                        recipes_data.append(
                            {"json": recipe_json, "image": None, "name": recipe_data.get("title", "Unknown")}
                        )

                except json.JSONDecodeError:
                    messages.error(request, _("Invalid JSON file"))
                    return redirect("settings")

        if not recipes_data:
            messages.warning(request, _("No recipes found in the uploaded file"))
            return redirect("settings")

        # Store recipes data in session for preview
        request.session["import_recipes"] = recipes_data
        request.session["import_format"] = import_format

        logger.info(f"Successfully parsed {len(recipes_data)} recipes for preview")
        return redirect("import_database_preview")

    except Exception as e:
        logger.error(f"Error processing import file: {e}", exc_info=True)
        messages.error(request, _("Error processing import file: %(error)s") % {"error": str(e)})
        return redirect("settings")


def import_database_preview(request: HttpRequest) -> HttpResponse:
    """Preview recipes before importing."""
    recipes_data = request.session.get("import_recipes")
    import_format = request.session.get("import_format")

    if not recipes_data:
        messages.warning(request, _("No import data found. Please upload a file first."))
        return redirect("settings")

    # Parse recipes to show preview information
    import json

    preview_recipes = []
    for recipe_data in recipes_data:
        try:
            recipe_json = json.loads(recipe_data["json"])

            # Get basic info based on format
            if import_format == "tandoor":
                preview_recipes.append(
                    {
                        "name": recipe_json.get("name", "Unknown"),
                        "description": recipe_json.get("description", "")[:200],
                        "servings": recipe_json.get("servings", "N/A"),
                        "steps_count": len(recipe_json.get("steps", [])),
                        "has_image": recipe_data.get("image") is not None,
                    }
                )
            else:  # plated
                ingredients_count = len(recipe_json.get("ingredients", []))
                preview_recipes.append(
                    {
                        "name": recipe_json.get("title", "Unknown"),
                        "description": recipe_json.get("description", "")[:200],
                        "servings": recipe_json.get("servings", "N/A"),
                        "ingredients_count": ingredients_count,
                        "steps_count": len(recipe_json.get("steps", [])),
                        "has_image": False,
                    }
                )
        except Exception as e:
            logger.warning(f"Error parsing recipe for preview: {e}")
            continue

    return render(
        request,
        "recipes/import_preview.html",
        {
            "recipes": preview_recipes,
            "recipes_count": len(preview_recipes),
            "import_format": import_format,
        },
    )


def import_database_confirm(request: HttpRequest) -> HttpResponse:
    """Confirm and save imported recipes to database."""
    if request.method != "POST":
        return redirect("import_database_preview")

    recipes_data = request.session.get("import_recipes")
    import_format = request.session.get("import_format")

    if not recipes_data:
        messages.warning(request, _("No import data found. Please upload a file first."))
        return redirect("settings")

    logger.info(f"Importing {len(recipes_data)} recipes to database")

    from django.core.files.base import ContentFile

    from ..models import RecipeImage
    from ..services.registry import format_registry

    imported_count = 0
    error_count = 0

    for recipe_data in recipes_data:
        try:
            recipe_json = recipe_data["json"]

            # Get the appropriate handler
            if import_format == "tandoor":
                handler = format_registry.get_handler("tandoor")
            else:
                handler = format_registry.get_handler("json")

            if not handler:
                logger.error(f"No handler found for format: {import_format}")
                error_count += 1
                continue

            # Import the recipe
            recipe = handler.import_recipe(recipe_json)

            # Handle image if present (Tandoor format)
            if recipe_data.get("image"):
                try:
                    import base64

                    # Decode base64 image data
                    image_bytes = base64.b64decode(recipe_data["image"])
                    image_content = ContentFile(image_bytes)
                    recipe_image = RecipeImage(recipe=recipe, order=0)
                    recipe_image.image.save(f"recipe_{recipe.pk}.jpg", image_content, save=True)
                    logger.debug(f"Saved image for recipe: {recipe.title}")
                except Exception as img_error:
                    logger.warning(f"Failed to save image for recipe {recipe.title}: {img_error}")

            imported_count += 1
            logger.debug(f"Imported recipe: {recipe.title}")

        except Exception as e:
            logger.error(f"Failed to import recipe: {e}", exc_info=True)
            error_count += 1
            continue

    # Clear session data
    if "import_recipes" in request.session:
        del request.session["import_recipes"]
    if "import_format" in request.session:
        del request.session["import_format"]

    # Show results
    if imported_count > 0:
        messages.success(request, _("Successfully imported %(count)d recipe(s)") % {"count": imported_count})

    if error_count > 0:
        messages.warning(request, _("Failed to import %(count)d recipe(s)") % {"count": error_count})

    logger.info(f"Import completed: {imported_count} successful, {error_count} failed")
    return redirect("recipe_list")
