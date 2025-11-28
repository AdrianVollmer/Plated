from __future__ import annotations

import logging
import threading

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from ..forms import AIRecipeExtractionForm
from ..models import AISettings
from ..services import ai_service

logger = logging.getLogger(__name__)


def ai_extract_recipe(request: HttpRequest) -> HttpResponse:
    """Extract a recipe using AI from text, HTML, or URL."""
    # Check if AI settings are configured
    ai_settings = AISettings.objects.first()
    if not ai_settings:
        messages.error(
            request,
            _("AI settings are not configured. Please configure AI settings in the settings page."),
        )
        return redirect("settings")

    if request.method == "POST":
        form = AIRecipeExtractionForm(request.POST)
        if form.is_valid():
            input_type = form.cleaned_data["input_type"]
            input_content = form.cleaned_data["input_content"]
            instructions = form.cleaned_data["prompt"]

            logger.info(f"AI recipe extraction initiated with input_type: {input_type}")

            # Check if we should run in background based on timeout
            timeout = ai_settings.timeout

            if timeout > 10:
                # Create and run background job
                return _create_background_job(request, input_type, input_content, instructions, timeout)
            else:
                # Run synchronously for quick jobs
                return _extract_recipe_sync(request, form, input_type, input_content, instructions, ai_settings)

    else:
        form = AIRecipeExtractionForm()

    return render(request, "recipes/ai_extract.html", {"form": form, "ai_settings": ai_settings})


def _create_background_job(
    request: HttpRequest, input_type: str, input_content: str, instructions: str, timeout: int
) -> HttpResponse:
    """Create a background job for AI extraction."""
    from ..models import AIJob

    job = AIJob.objects.create(
        status="pending",
        input_type=input_type,
        input_content=input_content,
        instructions=instructions,
        timeout=timeout,
    )
    logger.info(f"Created AI Job {job.pk} with timeout {timeout}s (background mode)")

    # Start the background task in a thread
    thread = threading.Thread(target=ai_service.process_ai_extraction_job, args=(job.pk,), daemon=True)
    thread.start()
    logger.debug(f"Started background thread for job {job.pk}")

    messages.success(
        request,
        _("Recipe extraction job started (timeout: %(timeout)ss). Check the Jobs page to see the result.")
        % {"timeout": timeout},
    )
    return redirect("jobs_list")


def _extract_recipe_sync(
    request: HttpRequest,
    form: AIRecipeExtractionForm,
    input_type: str,
    input_content: str,
    instructions: str,
    ai_settings: AISettings,
) -> HttpResponse:
    """Extract recipe synchronously and return the response."""
    logger.info(f"Running AI extraction synchronously (timeout: {ai_settings.timeout}s)")

    try:
        recipe_data = ai_service.extract_and_validate_recipe(input_type, input_content, ai_settings, instructions)

        # Store the recipe data in the session
        request.session["ai_extracted_recipe"] = recipe_data
        logger.info("Recipe extracted successfully via AI, redirecting to recipe form")
        messages.success(
            request,
            _("Recipe extracted successfully! Please review and save the recipe."),
        )
        return redirect("recipe_create")

    except ai_service.URLFetchError as e:
        logger.error(f"URL fetch error: {e}")
        messages.error(request, str(e))
        return render(request, "recipes/ai_extract.html", {"form": form})

    except ai_service.LLMAPIError as e:
        logger.error(f"LLM API error: {e}")
        messages.error(request, str(e))
        return render(request, "recipes/ai_extract.html", {"form": form})

    except ai_service.InvalidResponseError as e:
        logger.error(f"Invalid response error: {e}")
        messages.error(request, str(e))
        return render(request, "recipes/ai_extract.html", {"form": form})

    except Exception as e:
        logger.error(f"Unexpected error during AI recipe extraction: {e}", exc_info=True)
        messages.error(request, _("Unexpected error: %(error)s") % {"error": e})
        return render(request, "recipes/ai_extract.html", {"form": form})
