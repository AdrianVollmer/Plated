from __future__ import annotations

import json
import logging

import requests
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from ..forms import AIRecipeExtractionForm
from ..models import AISettings
from ..schema import get_recipe_json_schema, validate_recipe_data

logger = logging.getLogger(__name__)


def ai_extract_recipe(request: HttpRequest) -> HttpResponse:
    """Extract a recipe using AI from text, HTML, or URL."""
    # Check if AI settings are configured
    ai_settings = AISettings.objects.first()
    if not ai_settings:
        messages.error(
            request,
            "AI settings are not configured. Please configure AI settings in the settings page.",
        )
        return redirect("settings")

    if request.method == "POST":
        form = AIRecipeExtractionForm(request.POST)
        if form.is_valid():
            input_type = form.cleaned_data["input_type"]
            input_content = form.cleaned_data["input_content"]
            prompt = form.cleaned_data["prompt"]

            logger.info(f"AI recipe extraction initiated with input_type: {input_type}")

            try:
                prompt_ai(input_type, input_content, request, form, prompt, ai_settings)
            except Exception as e:
                logger.error(f"Unexpected error during AI recipe extraction: {e}", exc_info=True)
                messages.error(request, f"Unexpected error: {e}")
                return render(request, "recipes/ai_extract.html", {"form": form})

    else:
        form = AIRecipeExtractionForm()

    return render(request, "recipes/ai_extract.html", {"form": form})


def prompt_ai(
    input_type: str,
    input_content: str,
    request: HttpRequest,
    form: AIRecipeExtractionForm,
    prompt,
    ai_settings,
) -> HttpResponse:
    # Fetch content if it's a URL
    if input_type == "url":
        logger.debug(f"Fetching content from URL: {input_content}")
        try:
            response = requests.get(input_content, timeout=30)
            response.raise_for_status()
            content = response.text
            logger.debug(f"URL content fetched successfully: {len(content)} characters")
        except requests.RequestException as e:
            logger.error(f"Error fetching URL {input_content}: {e}")
            messages.error(request, f"Error fetching URL: {e}")
            return render(request, "recipes/ai_extract.html", {"form": form})
    else:
        content = input_content

    # Build the prompt for the LLM
    schema_description = """
Extract the recipe information from the provided content and return it as a JSON object"""

    # Get the JSON schema for recipe extraction
    recipe_schema = get_recipe_json_schema()

    system_message = schema_description
    if prompt:
        system_message += f"\n\nAdditional instructions: {prompt}"

    # Call the LLM API
    try:
        prompt = system_message + "\n\n" + content
        return call_llm_api(request, form, ai_settings, prompt, recipe_schema)

    except requests.RequestException as e:
        server_error = ""
        try:
            if e.response is not None:
                server_error = e.response.json()["error"]
        except KeyError:
            pass
        error_msg = f"Error calling LLM API: {e}: {server_error}"
        logger.error(error_msg)
        messages.error(request, error_msg)
        return render(request, "recipes/ai_extract.html", {"form": form})


def call_llm_api(
    request: HttpRequest, form: AIRecipeExtractionForm, ai_settings: AISettings, prompt: str, recipe_schema
) -> HttpResponse:
    # Try OpenAI-compatible API format
    api_payload = {
        "model": ai_settings.model,
        "prompt": prompt,
        "options": {
            "temperature": ai_settings.temperature,
        },
        "format": recipe_schema,
        "stream": False,
    }

    logger.debug(f"Calling LLM API: {ai_settings.api_url} / {api_payload}")

    api_response = requests.post(
        ai_settings.api_url,
        headers={
            "Authorization": f"Bearer {ai_settings.api_key}",
            "Content-Type": "application/json",
        },
        json=api_payload,
        timeout=120,
    )
    api_response.raise_for_status()
    response_data = api_response.json()

    logger.debug("LLM API call successful")

    # Extract the response text (try OpenAI format first)
    if "choices" in response_data and len(response_data["choices"]) > 0:
        recipe_json_str = response_data["choices"][0]["message"]["content"]
    elif "content" in response_data:
        # Alternative format
        recipe_json_str = response_data["content"]
    elif "response" in response_data:
        recipe_json_str = response_data["response"]
    else:
        logger.error(f"Unexpected API response format: {response_data}")
        messages.error(
            request,
            "Unexpected response format from AI API. Please check your API configuration.",
        )
        return render(request, "recipes/ai_extract.html", {"form": form})

    # Clean up the response (remove markdown code blocks if present)
    recipe_json_str = recipe_json_str.strip()
    if recipe_json_str.startswith("```json"):
        recipe_json_str = recipe_json_str[7:]
    if recipe_json_str.startswith("```"):
        recipe_json_str = recipe_json_str[3:]
    if recipe_json_str.endswith("```"):
        recipe_json_str = recipe_json_str[:-3]
    recipe_json_str = recipe_json_str.strip()

    # Parse the JSON
    try:
        recipe_data = json.loads(recipe_json_str)
        logger.debug("Recipe JSON parsed successfully")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing recipe JSON: {e}\nJSON string: {recipe_json_str[:500]}")
        messages.error(
            request,
            f"Error parsing AI response as JSON: {e}. The AI may have returned invalid JSON.",
        )
        return render(request, "recipes/ai_extract.html", {"form": form})

    # Validate the recipe data
    errors = validate_recipe_data(recipe_data)
    if errors:
        logger.warning(f"AI-extracted recipe validation failed: {len(errors)} errors")
        for error in errors[:5]:  # Show first 5 errors
            messages.error(request, f"Validation error: {error}")
        return render(request, "recipes/ai_extract.html", {"form": form})

    # Store the recipe data in the session
    request.session["ai_extracted_recipe"] = recipe_data
    logger.info("Recipe extracted successfully via AI, redirecting to recipe form")
    messages.success(
        request,
        "Recipe extracted successfully! Please review and save the recipe.",
    )
    return redirect("recipe_create")
