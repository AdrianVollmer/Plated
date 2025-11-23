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
        - has_any_jobs: Whether user has any jobs at all
    """
    unseen_jobs_count = AIJob.objects.filter(seen=False, status__in=["completed", "failed"]).count()
    has_any_jobs = AIJob.objects.exists()

    return {
        "unseen_jobs_count": unseen_jobs_count,
        "has_any_jobs": has_any_jobs,
    }
