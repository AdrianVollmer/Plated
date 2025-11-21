from __future__ import annotations

import logging
from pathlib import Path

from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger(__name__)


def manifest_view(request: HttpRequest) -> JsonResponse:
    """Serve the PWA manifest with proper content type."""
    from django.templatetags.static import static

    manifest = {
        "name": "Plated - Recipe Manager",
        "short_name": "Plated",
        "description": "Your personal recipe manager for organizing, creating, and sharing recipes",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#0d6efd",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": request.build_absolute_uri(static("icons/icon-72x72.png")),
                "sizes": "72x72",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-96x96.png")),
                "sizes": "96x96",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-128x128.png")),
                "sizes": "128x128",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-144x144.png")),
                "sizes": "144x144",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-152x152.png")),
                "sizes": "152x152",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-192x192.png")),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-384x384.png")),
                "sizes": "384x384",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-512x512.png")),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
        ],
    }
    return JsonResponse(manifest, content_type="application/manifest+json")


def service_worker_view(request: HttpRequest) -> HttpResponse:
    """Serve the service worker from the static directory."""
    from django.conf import settings

    service_worker_path = Path(settings.BASE_DIR) / "static" / "service-worker.js"

    try:
        with open(service_worker_path, encoding="utf-8") as f:
            content = f.read()
        return HttpResponse(content, content_type="application/javascript")
    except FileNotFoundError:
        logger.error(f"Service worker not found at {service_worker_path}")
        return HttpResponse("Service worker not found", status=404)
