"""Service for generating PDFs using the Typst template engine."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TypstError(Exception):
    """Base exception for Typst-related errors."""


class TypstTemplateNotFoundError(TypstError):
    """Raised when a Typst template file is not found."""


class TypstCompilationError(TypstError):
    """Raised when Typst compilation fails."""


class TypstExecutableNotFoundError(TypstError):
    """Raised when the Typst executable is not found on the system."""


class TypstTimeoutError(TypstError):
    """Raised when Typst compilation times out."""


def generate_typst_pdf(
    template_name: str,
    data: dict[str, Any],
    context_name: str,
    entity_name: str,
    entity_id: int,
    additional_files: dict[str, Path] | None = None,
    timeout: int = 60,
) -> bytes:
    """
    Generate a PDF using Typst template engine.

    Args:
        template_name: Name of the .typ template file (e.g., "meal_plan.typ")
        data: Dictionary to serialize to JSON for the template
        context_name: Name of the JSON context file (e.g., "meal_plan")
        entity_name: Entity type for logging (e.g., "meal plan")
        entity_id: ID of the entity for logging
        additional_files: Optional dict of additional files to copy to temp dir
                         (key: filename, value: source path)
        timeout: Timeout in seconds for Typst compilation (default: 60)

    Returns:
        PDF file content as bytes

    Raises:
        TypstTemplateNotFoundError: If the template file is not found
        TypstExecutableNotFoundError: If Typst is not installed
        TypstTimeoutError: If compilation times out
        TypstCompilationError: If compilation fails
        TypstError: For any other unexpected errors
    """
    logger.info(f"PDF generation initiated for {entity_name} (ID: {entity_id})")

    # Get the path to the Typst template
    base_dir = Path(__file__).resolve().parent.parent
    typst_template = base_dir / "typst" / template_name

    if not typst_template.exists():
        logger.error(f"Typst template not found at {typst_template}")
        raise TypstTemplateNotFoundError(f"Typst template file not found: {template_name}")

    try:
        # Create temporary directory for intermediate files
        with tempfile.TemporaryDirectory(prefix="plated_typst_") as temp_dir:
            temp_path = Path(temp_dir)
            logger.debug(f"Using temporary directory: {temp_dir}")

            # Copy typst template to temp directory
            temp_typst = temp_path / template_name
            shutil.copy(typst_template, temp_typst)

            # Copy any additional files to temp directory
            if additional_files:
                for filename, source_path in additional_files.items():
                    dest_path = temp_path / filename
                    shutil.copy(source_path, dest_path)

            # Write data JSON to temp directory
            json_filename = f"{context_name}.json"
            json_path = temp_path / json_filename
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Prepare output PDF path
            output_pdf = temp_path / f"{context_name}.pdf"

            # Prepare Typst input data with relative paths
            typst_input_data = json.dumps({context_name: json_filename})

            # Call Typst to compile the PDF
            try:
                logger.debug(f"Running Typst compiler for {entity_name} (ID: {entity_id})")
                subprocess.run(
                    [
                        "typst",
                        "compile",
                        str(temp_typst),
                        str(output_pdf),
                        "--input",
                        f"data={typst_input_data}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=True,
                )
            except FileNotFoundError as e:
                logger.error("Typst executable not found on system")
                raise TypstExecutableNotFoundError(
                    "Typst is not installed. Please install Typst to generate PDFs."
                ) from e
            except subprocess.TimeoutExpired as e:
                logger.error(f"Typst compilation timed out for {entity_name} (ID: {entity_id})")
                raise TypstTimeoutError(f"PDF generation timed out after {timeout} seconds.") from e
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Typst compilation failed for {entity_name} (ID: {entity_id}): {e.stderr}",
                    exc_info=True,
                )
                error_message = e.stderr if e.stderr else str(e)
                raise TypstCompilationError(f"Error generating PDF: {error_message}") from e

            # Check if PDF was created
            if not output_pdf.exists():
                logger.error(f"PDF file not created for {entity_name} (ID: {entity_id})")
                raise TypstCompilationError("PDF file was not generated.")

            # Read the PDF file
            with open(output_pdf, "rb") as pdf_file:
                pdf_content = pdf_file.read()

            logger.info(f"PDF generated successfully for {entity_name} (ID: {entity_id})")
            return pdf_content

    except TypstError:
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        # Wrap any other unexpected errors
        logger.error(
            f"Unexpected error generating PDF for {entity_name} (ID: {entity_id}): {e}",
            exc_info=True,
        )
        raise TypstError(f"Unexpected error generating PDF: {e}") from e


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string to be used as a filename.

    Replaces non-alphanumeric characters (except spaces, hyphens, underscores)
    with underscores, then replaces spaces with underscores.

    Args:
        name: The string to sanitize

    Returns:
        Sanitized filename-safe string
    """
    safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in name)
    safe_name = safe_name.replace(" ", "_")
    return safe_name
