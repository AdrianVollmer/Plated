from __future__ import annotations

import logging

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import translation

from ..forms import AISettingsForm, UserSettingsForm
from ..models import AISettings, UserSettings

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
                request.session["django_language"] = language
                messages.success(request, "Language settings saved successfully!")
                logger.info(f"Language settings updated to {language}")
                return redirect("settings")
        # Handle AI settings form submission
        elif "ai_settings" in request.POST:
            if ai_settings:
                ai_form = AISettingsForm(request.POST, instance=ai_settings)
            else:
                ai_form = AISettingsForm(request.POST)

            if ai_form.is_valid():
                ai_form.save()
                messages.success(request, "AI settings saved successfully!")
                logger.info("AI settings updated")
                return redirect("settings")

    # Initialize forms for GET request
    user_form = UserSettingsForm(instance=user_settings)
    ai_form = AISettingsForm(instance=ai_settings) if ai_settings else AISettingsForm()

    return render(
        request,
        "recipes/settings.html",
        {
            "user_settings": user_settings,
            "user_form": user_form,
            "ai_settings": ai_settings,
            "ai_form": ai_form,
        },
    )
