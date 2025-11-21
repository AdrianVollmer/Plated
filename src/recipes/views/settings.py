from __future__ import annotations

import logging

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from ..forms import AISettingsForm
from ..models import AISettings

logger = logging.getLogger(__name__)


def settings_view(request: HttpRequest) -> HttpResponse:
    """Display application settings page."""
    # Since we only support one set of AI settings, get or create it
    ai_settings = AISettings.objects.first()

    if request.method == "POST" and "ai_settings" in request.POST:
        if ai_settings:
            ai_form = AISettingsForm(request.POST, instance=ai_settings)
        else:
            ai_form = AISettingsForm(request.POST)

        if ai_form.is_valid():
            ai_form.save()
            messages.success(request, "AI settings saved successfully!")
            logger.info("AI settings updated")
            return redirect("settings")
    else:
        ai_form = AISettingsForm(instance=ai_settings) if ai_settings else AISettingsForm()

    return render(
        request,
        "recipes/settings.html",
        {"ai_settings": ai_settings, "ai_form": ai_form},
    )
