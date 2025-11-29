"""Service for AI recipe extraction operations."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import requests
from django.utils import timezone

from ..schemas import get_recipe_json_schema, validate_recipe_data

if TYPE_CHECKING:
    from ..models import AISettings

logger = logging.getLogger(__name__)


class AIExtractionError(Exception):
    """Base exception for AI extraction errors."""

    pass


class URLFetchError(AIExtractionError):
    """Error fetching content from URL."""

    pass


class LLMAPIError(AIExtractionError):
    """Error calling LLM API."""

    pass


class InvalidResponseError(AIExtractionError):
    """Error parsing or validating LLM response."""

    pass


def fetch_url_content(url: str, timeout: int = 30) -> str:
    """
    Fetch content from a URL.

    Args:
        url: The URL to fetch content from
        timeout: Request timeout in seconds

    Returns:
        The fetched content as a string

    Raises:
        URLFetchError: If the URL cannot be fetched
    """
    logger.debug(f"Fetching content from URL: {url}")
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        content = response.text
        logger.debug(f"URL content fetched successfully: {len(content)} characters")
        return content
    except requests.RequestException as e:
        logger.error(f"Error fetching URL {url}: {e}")
        raise URLFetchError(f"Error fetching URL: {e}") from e


def build_prompt(content: str, instructions: str | None = None) -> str:
    """
    Build the prompt for the LLM.

    Args:
        content: The content to extract recipe from
        instructions: Optional additional instructions

    Returns:
        The complete prompt string
    """
    schema_description = "Extract the recipe information from the provided content and return it as a JSON object"

    system_message = schema_description
    if instructions:
        system_message += f"\n\nAdditional instructions: {instructions}"

    prompt = system_message + "\n\n" + content
    return prompt


def parse_llm_response(response_data: dict) -> str:
    """
    Parse the LLM API response to extract the recipe JSON string.

    Args:
        response_data: The JSON response from the LLM API

    Returns:
        The extracted recipe JSON string

    Raises:
        InvalidResponseError: If the response format is unexpected
    """
    # Extract the response text (try different formats)
    if "choices" in response_data and len(response_data["choices"]) > 0:
        recipe_json_str = response_data["choices"][0]["message"]["content"]
    elif "content" in response_data:
        recipe_json_str = response_data["content"]
    elif "response" in response_data:
        recipe_json_str = response_data["response"]
    else:
        logger.error(f"Unexpected API response format: {response_data}")
        raise InvalidResponseError("Unexpected response format from AI API. Please check your API configuration.")

    return recipe_json_str


def clean_json_response(json_str: str) -> str:
    """
    Clean up JSON response by removing markdown code blocks.

    Args:
        json_str: The raw JSON string from LLM

    Returns:
        Cleaned JSON string
    """
    json_str = json_str.strip()
    if json_str.startswith("```json"):
        json_str = json_str[7:]
    if json_str.startswith("```"):
        json_str = json_str[3:]
    if json_str.endswith("```"):
        json_str = json_str[:-3]
    return json_str.strip()


def call_llm_api(
    ai_settings: AISettings,
    prompt: str,
    recipe_schema: dict,
    timeout: int | None = None,
) -> dict:
    """
    Call the LLM API with the given prompt.

    Args:
        ai_settings: AI settings containing API configuration
        prompt: The prompt to send to the LLM
        recipe_schema: The JSON schema for recipe extraction
        timeout: Optional timeout override (uses ai_settings.timeout if None)

    Returns:
        The parsed recipe data as a dictionary

    Raises:
        LLMAPIError: If the API call fails
        InvalidResponseError: If the response cannot be parsed or validated
    """
    api_payload = {
        "model": ai_settings.model,
        "prompt": prompt,
        "options": {
            "temperature": ai_settings.temperature,
        },
        "format": recipe_schema,
        "stream": False,
    }

    timeout_value = timeout if timeout is not None else ai_settings.timeout
    logger.debug(f"Calling LLM API: {ai_settings.api_url} / {api_payload}")

    try:
        api_response = requests.post(
            ai_settings.api_url,
            headers={
                "Authorization": f"Bearer {ai_settings.api_key}",
                "Content-Type": "application/json",
            },
            json=api_payload,
            timeout=timeout_value,
        )
        api_response.raise_for_status()
        response_data = api_response.json()
    except requests.RequestException as e:
        server_error = ""
        try:
            if e.response is not None:
                server_error = e.response.json().get("error", "")
        except (KeyError, json.JSONDecodeError):
            pass
        error_msg = f"Error calling LLM API: {e}"
        if server_error:
            error_msg += f": {server_error}"
        logger.error(error_msg)
        raise LLMAPIError(error_msg) from e

    logger.debug("LLM API call successful")

    # Parse and extract the response
    recipe_json_str = parse_llm_response(response_data)

    # Clean up the response
    recipe_json_str = clean_json_response(recipe_json_str)

    # Parse the JSON
    try:
        recipe_data = json.loads(recipe_json_str)
        logger.debug("Recipe JSON parsed successfully")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing recipe JSON: {e}\nJSON string: {recipe_json_str[:500]}")
        raise InvalidResponseError(
            f"Error parsing AI response as JSON: {e}. The AI may have returned invalid JSON."
        ) from e

    # Validate the recipe data
    errors = validate_recipe_data(recipe_data)
    if errors:
        logger.warning(f"AI-extracted recipe validation failed: {len(errors)} errors")
        error_msg = f"Validation failed: {'; '.join(errors[:3])}"
        if len(errors) > 3:
            error_msg += f" (and {len(errors) - 3} more errors)"
        raise InvalidResponseError(error_msg)

    logger.debug(f"AI extraction result: {recipe_data}")
    return recipe_data


def extract_and_validate_recipe(
    input_type: str,
    input_content: str,
    ai_settings: AISettings,
    instructions: str | None = None,
    timeout: int | None = None,
) -> dict:
    """
    Extract and validate a recipe from input content using AI.

    Args:
        input_type: Type of input ('url', 'text', or 'html')
        input_content: The input content or URL
        ai_settings: AI settings containing API configuration
        instructions: Optional additional instructions for the LLM
        timeout: Optional timeout override

    Returns:
        The extracted and validated recipe data

    Raises:
        URLFetchError: If fetching URL fails
        LLMAPIError: If the API call fails
        InvalidResponseError: If the response is invalid
    """
    # Fetch content if it's a URL
    if input_type == "url":
        content = fetch_url_content(input_content, timeout=30)
    else:
        content = input_content

    # Build the prompt
    prompt = build_prompt(content, instructions)

    # Get the JSON schema
    recipe_schema = get_recipe_json_schema()

    # Call the LLM API and get validated recipe data
    recipe_data = call_llm_api(ai_settings, prompt, recipe_schema, timeout)

    logger.info("Recipe extracted successfully via AI")
    return recipe_data


def process_ai_extraction_job(job_id: int) -> None:
    """
    Process an AI recipe extraction job in a background thread.

    Args:
        job_id: ID of the AIJob to process
    """
    from ..models import AIJob, AISettings

    try:
        job = AIJob.objects.get(pk=job_id)
    except AIJob.DoesNotExist:
        logger.error(f"AI Job {job_id} not found")
        return

    # Check if job is already cancelled
    if job.status == "cancelled":
        logger.info(f"AI Job {job_id} was cancelled before processing")
        return

    # Mark job as running
    job.status = "running"
    job.started_at = timezone.now()
    job.save()

    logger.info(f"Starting AI Job {job_id} (timeout: {job.timeout}s)")

    try:
        # Get AI settings
        ai_settings = AISettings.objects.first()
        if not ai_settings:
            raise Exception("AI settings not configured")

        # Extract and validate recipe
        recipe_data = extract_and_validate_recipe(
            job.input_type,
            job.input_content,
            ai_settings,
            job.instructions,
            job.timeout,
        )

        # Mark job as completed
        job.status = "completed"
        job.result_data = recipe_data
        job.completed_at = timezone.now()
        job.save()

        logger.info(f"AI Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"AI Job {job_id} failed: {e}", exc_info=True)
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = timezone.now()
        job.save()
