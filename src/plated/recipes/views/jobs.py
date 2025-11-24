from __future__ import annotations

import logging

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from ..models import AIJob
from ..views.ai import process_ai_extraction_job

logger = logging.getLogger(__name__)


def jobs_list(request: HttpRequest) -> HttpResponse:
    """Display list of all AI extraction jobs."""
    jobs = AIJob.objects.all().order_by("-created_at")
    return render(request, "recipes/jobs_list.html", {"jobs": jobs})


def job_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Display details of a specific AI extraction job."""
    job = get_object_or_404(AIJob, pk=pk)

    # Mark as seen if completed or failed
    if job.status in ["completed", "failed"] and not job.seen:
        job.seen = True
        job.save()
        logger.info(f"Marked AI Job {pk} as seen")

    return render(request, "recipes/job_detail.html", {"job": job})


def job_cancel(request: HttpRequest, pk: int) -> HttpResponse:
    """Cancel a running or pending AI extraction job."""
    if request.method != "POST":
        return redirect("jobs_list")

    job = get_object_or_404(AIJob, pk=pk)

    if job.status in ["pending", "running"]:
        job.status = "cancelled"
        job.save()
        logger.info(f"AI Job {pk} cancelled by user")
        messages.success(request, _("Job #%(id)s has been cancelled.") % {"id": pk})
    else:
        messages.error(
            request,
            _("Cannot cancel job #%(id)s - it is %(status)s.") % {"id": pk, "status": job.get_status_display()},
        )

    return redirect("job_detail", pk=pk)


def job_retry(request: HttpRequest, pk: int) -> HttpResponse:
    """Retry a failed AI extraction job."""
    if request.method != "POST":
        return redirect("jobs_list")

    job = get_object_or_404(AIJob, pk=pk)

    if job.status != "failed":
        messages.error(
            request,
            _("Cannot retry job #%(id)s - it is %(status)s.") % {"id": pk, "status": job.get_status_display()},
        )
        return redirect("job_detail", pk=pk)

    # Create a new job with same parameters
    new_job = AIJob.objects.create(
        status="pending",
        input_type=job.input_type,
        input_content=job.input_content,
        instructions=job.instructions,
        timeout=job.timeout,
    )
    logger.info(f"Created new AI Job {new_job.pk} as retry of job {pk}")

    # Queue the background task
    process_ai_extraction_job(new_job.pk)

    messages.success(
        request,
        _("Job #%(old_id)s has been requeued as job #%(new_id)s.") % {"old_id": pk, "new_id": new_job.pk},
    )
    return redirect("job_detail", pk=new_job.pk)


def job_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete an AI extraction job."""
    if request.method != "POST":
        return redirect("jobs_list")

    job = get_object_or_404(AIJob, pk=pk)

    if job.status in ["pending", "running"]:
        messages.error(
            request,
            _("Cannot delete job #%(id)s while it is %(status)s. Cancel it first.")
            % {"id": pk, "status": job.get_status_display()},
        )
        return redirect("job_detail", pk=pk)

    logger.info(f"Deleting AI Job {pk} (status: {job.status})")
    job.delete()
    messages.success(request, _("Job #%(id)s has been deleted.") % {"id": pk})
    return redirect("jobs_list")


def job_mark_seen(request: HttpRequest, pk: int) -> HttpResponse:
    """Mark a job as seen (AJAX endpoint)."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    job = get_object_or_404(AIJob, pk=pk)
    job.seen = True
    job.save()
    logger.debug(f"Marked AI Job {pk} as seen via AJAX")

    return JsonResponse({"success": True})


def api_job_status(request: HttpRequest, pk: int) -> JsonResponse:
    """API endpoint to check job status (for polling)."""
    job = get_object_or_404(AIJob, pk=pk)

    return JsonResponse(
        {
            "id": job.pk,
            "status": job.status,
            "status_display": job.get_status_display(),
            "error_message": job.error_message if job.status == "failed" else None,
            "has_result": job.result_data is not None,
        }
    )


def job_use_result(request: HttpRequest, pk: int) -> HttpResponse:
    """Use the result of a completed job to create a recipe."""
    job = get_object_or_404(AIJob, pk=pk)

    if job.status != "completed" or not job.result_data:
        messages.error(request, _("Job #%(id)s does not have a completed result to use.") % {"id": pk})
        return redirect("job_detail", pk=pk)

    # Store the result in session and redirect to recipe create
    request.session["ai_extracted_recipe"] = job.result_data
    logger.info(f"Using result from AI Job {pk} for recipe creation")
    messages.success(request, _("Recipe data loaded from job. Please review and save the recipe."))

    return redirect("recipe_create")
