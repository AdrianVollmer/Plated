"""Service for database export operations."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Base exception for export errors."""

    pass


def get_database_path() -> Path:
    """
    Get the path to the SQLite database file.

    Returns:
        Path to the database file

    Raises:
        ExportError: If database is not SQLite or path not found
    """
    db_settings = settings.DATABASES.get("default", {})
    engine = db_settings.get("ENGINE", "")

    if "sqlite" not in engine.lower():
        raise ExportError("Database export is only supported for SQLite databases")

    db_path = db_settings.get("NAME")
    if not db_path:
        raise ExportError("Database path not found in settings")

    db_file = Path(db_path)
    if not db_file.exists():
        raise ExportError(f"Database file not found: {db_path}")

    return db_file


def export_sqlite_database() -> bytes:
    """
    Export the SQLite database file.

    Returns:
        Database file contents as bytes

    Raises:
        ExportError: If export fails
    """
    logger.info("SQLite database export initiated")

    try:
        db_path = get_database_path()

        # Read the database file
        with open(db_path, "rb") as f:
            db_content = f.read()

        logger.info(f"SQLite database exported successfully ({len(db_content)} bytes)")
        return db_content

    except Exception as e:
        error_msg = f"Failed to export SQLite database: {e}"
        logger.error(error_msg)
        raise ExportError(error_msg) from e


def export_json_database() -> str:
    """
    Export the entire database as JSON.

    Uses Django's dumpdata command to serialize all data.

    Returns:
        JSON string containing all database data

    Raises:
        ExportError: If export fails
    """
    logger.info("JSON database export initiated")

    try:
        # Use Django's dumpdata to serialize all data
        from io import StringIO

        from django.core.management import call_command

        output = StringIO()
        call_command(
            "dumpdata",
            "--natural-foreign",
            "--natural-primary",
            "--indent",
            "2",
            exclude=["contenttypes", "auth.permission", "sessions.session"],
            stdout=output,
        )
        json_content = output.getvalue()

        logger.info(f"JSON database exported successfully ({len(json_content)} characters)")
        return json_content

    except Exception as e:
        error_msg = f"Failed to export database as JSON: {e}"
        logger.error(error_msg)
        raise ExportError(error_msg) from e


def export_sql_dump() -> str:
    """
    Export the database as SQL dump.

    For SQLite, uses the .dump command via sqlite3 CLI.

    Returns:
        SQL dump as string

    Raises:
        ExportError: If export fails
    """
    logger.info("SQL dump export initiated")

    try:
        db_path = get_database_path()

        # Use sqlite3 command line tool to create SQL dump
        # Run sqlite3 with trusted database path only
        result = subprocess.run(  # noqa: S603, S607
            ["sqlite3", str(db_path), ".dump"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )

        sql_dump = result.stdout

        logger.info(f"SQL dump exported successfully ({len(sql_dump)} characters)")
        return sql_dump

    except FileNotFoundError as e:
        error_msg = "sqlite3 command not found. Please install SQLite3 CLI tools."
        logger.error(error_msg)
        raise ExportError(error_msg) from e
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to create SQL dump: {e.stderr}"
        logger.error(error_msg)
        raise ExportError(error_msg) from e
    except Exception as e:
        error_msg = f"Failed to export SQL dump: {e}"
        logger.error(error_msg)
        raise ExportError(error_msg) from e


def get_export_filename(format_type: str) -> str:
    """
    Generate a filename for the export.

    Args:
        format_type: Export format (sqlite, json, sql)

    Returns:
        Filename with timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    extensions = {
        "sqlite": "db",
        "json": "json",
        "sql": "sql",
    }

    ext = extensions.get(format_type, "txt")
    return f"plated_export_{timestamp}.{ext}"


def get_available_export_formats() -> list[dict[str, str]]:
    """
    Get list of available export formats.

    Returns:
        List of dicts with format info
    """
    formats = [
        {
            "id": "sqlite",
            "name": "SQLite Database",
            "description": "Complete SQLite database file (.db)",
            "mime_type": "application/x-sqlite3",
        },
        {
            "id": "json",
            "name": "JSON",
            "description": "All data in JSON format (.json)",
            "mime_type": "application/json",
        },
        {
            "id": "sql",
            "name": "SQL Dump",
            "description": "SQL statements to recreate database (.sql)",
            "mime_type": "text/plain",
        },
    ]

    return formats
