#!/usr/bin/env python
"""Entry point to run the Plated development server.

This script:
1. Sets up environment variables (DEBUG=True, SECRET_KEY, DATABASE_URL)
2. Creates the database directory in XDG_DATA_HOME/plated
3. Runs the seed_db management command (only if DB doesn't exist)
4. Starts the development server
"""

import hashlib
import os
import socket
import sys
from pathlib import Path


def generate_secret_key() -> str:
    """Generate a host-specific secret key based on hostname."""
    hostname = socket.gethostname()
    # Create a deterministic but unique secret key for this host
    secret_base = f"plated-dev-{hostname}"
    return hashlib.sha256(secret_base.encode()).hexdigest()


def get_data_dir() -> Path:
    """Get the XDG data directory for Plated."""
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        data_dir = Path(xdg_data_home) / "plated"
    else:
        data_dir = Path.home() / ".local" / "share" / "plated"
    return data_dir


def main() -> None:
    """Run the development server with proper environment setup."""
    # Set up data directory and database path
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "db.sqlite3"
    db_exists = db_path.exists()

    # Set up environment variables
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ["DEBUG"] = "True"
    os.environ["SECRET_KEY"] = generate_secret_key()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["PLATED_BANNER_TEXT"] = "Demo mode. Do not use in production."
    os.environ["PLATED_BANNER_COLOR"] = "danger"

    # Log database URL
    print(f"Database URL: sqlite:///{db_path}")

    # Add the plated package directory to Python path so Django can find config.settings
    package_dir = Path(__file__).parent
    sys.path.insert(0, str(package_dir))

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Run migrations to ensure database schema is up to date
    print("Running migrations...")
    execute_from_command_line(["manage.py", "migrate", "--noinput"])

    # Only seed database if it didn't exist before
    if not db_exists:
        print("\nDatabase is new, running seed_db command...")
        execute_from_command_line(["manage.py", "seed_db"])
    else:
        print("\nDatabase already exists, skipping seed_db.")

    # Run development server
    print("\nStarting development server...")
    execute_from_command_line(["manage.py", "runserver"])


if __name__ == "__main__":
    main()
