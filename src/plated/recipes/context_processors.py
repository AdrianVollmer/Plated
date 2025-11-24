from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from .models import AIJob


def jobs_context(request: HttpRequest) -> dict[str, Any]:
    """
    Add job-related context variables to all templates.

    Returns:
        Dictionary with:
        - unseen_jobs_count: Number of unseen completed/failed jobs
    """
    unseen_jobs_count = AIJob.objects.filter(seen=False, status__in=["completed", "failed"]).count()

    return {
        "unseen_jobs_count": unseen_jobs_count,
    }


def version_context(request: HttpRequest) -> dict[str, Any]:
    """
    Add version information to all templates.

    Returns:
        Dictionary with:
        - app_version: Application version from VCS
    """
    try:
        from plated._version import __version__  # type: ignore[import-untyped]
    except ImportError:
        __version__ = "unknown"

    return {
        "app_version": __version__,
    }
