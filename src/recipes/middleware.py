from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from .models import UserSettings

# Django's LocaleMiddleware uses this session key
LANGUAGE_SESSION_KEY = "_language"


class UserLanguageMiddleware:
    """Middleware to set user's preferred language from UserSettings."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Ensure session exists
        if not request.session.session_key:
            request.session.create()

        # Try to get user's language preference from database
        try:
            user_settings = UserSettings.objects.get(session_key=request.session.session_key)
            # Set the language in the session for LocaleMiddleware to pick up
            if user_settings.language:
                request.session[LANGUAGE_SESSION_KEY] = user_settings.language
        except UserSettings.DoesNotExist:
            # No user settings yet, will use default language
            pass

        response = self.get_response(request)
        return response
