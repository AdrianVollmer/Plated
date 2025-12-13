from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import translation

from .models import UserSettings

# Django's LocaleMiddleware uses this session key
LANGUAGE_SESSION_KEY = "_language"


class UserLanguageMiddleware:
    """Middleware to set user's preferred language and locale from UserSettings."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Ensure session exists
        if not request.session.session_key:
            request.session.create()

        # Try to get user's language and locale preferences from database
        user_language = None
        user_locale = None
        try:
            user_settings = UserSettings.objects.get(session_key=request.session.session_key)
            # Set the language in the session for LocaleMiddleware to pick up
            if user_settings.language:
                user_language = user_settings.language
                request.session[LANGUAGE_SESSION_KEY] = user_language

            # Activate the user's locale for number/date formatting
            if user_settings.locale:
                user_locale = user_settings.locale
                # Activate the locale for this request
                translation.activate(user_locale)
                # Store locale on request for template context
                request.LANGUAGE_CODE = user_locale
        except UserSettings.DoesNotExist:
            # No user settings yet, will use default language
            pass

        response = self.get_response(request)

        # Set language cookie to persist across requests
        if user_language:
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_language)

        # Deactivate locale after response is generated
        translation.deactivate()

        return response
