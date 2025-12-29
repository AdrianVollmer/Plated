#!/usr/bin/env python
"""Entry point to run the Plated development server.

This script:
1. Sets up environment variables (DEBUG=True, SECRET_KEY)
2. Runs the seed_db management command
3. Starts the development server
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


def main() -> None:
    """Run the development server with proper environment setup."""
    # Set up environment variables
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ["DEBUG"] = "True"
    os.environ["SECRET_KEY"] = generate_secret_key()

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

    # Run seed_db command
    print("Running seed_db command...")
    execute_from_command_line(["manage.py", "seed_db"])

    # Run development server
    print("\nStarting development server...")
    execute_from_command_line(["manage.py", "runserver"])


if __name__ == "__main__":
    main()
