from __future__ import annotations

import logging

from django.conf import settings as django_settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.translation import gettext as _

from ..forms import AISettingsForm, UserSettingsForm
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

    return render(
        request,
        "recipes/settings.html",
        {
            "user_settings": user_settings,
            "user_form": user_form,
            "ai_settings": ai_settings,
            "ai_form": ai_form,
            "export_formats": export_formats,
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
