"""URL configuration for testviews tests."""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("recipes.urls")),
    path("admin/", admin.site.urls),
    # Always include testviews for testing
    path("testviews/", include("recipes.testviews_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # type: ignore
