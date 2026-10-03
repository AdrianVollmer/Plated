"""Screenshot every view in the app at mobile and desktop viewports.

Run against an already-seeded dev database:

    uv run python src/plated/recipes/management/commands/seed_testdata.py

Requires the Chromium browser installed once via:

    uv run playwright install chromium

Usage:

    uv run scripts/screenshot_views.py
"""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("screenshot_views")

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src" / "plated"
OUTPUT_DIR = REPO_ROOT / "screenshots"

MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

VIEWPORTS: dict[str, dict[str, Any]] = {
    "mobile": {
        "viewport": {"width": 390, "height": 844},
        "device_scale_factor": 2,
        "is_mobile": True,
        "user_agent": MOBILE_USER_AGENT,
    },
    "desktop": {"viewport": {"width": 1440, "height": 900}},
}


@dataclass(frozen=True)
class ViewSpec:
    name: str
    path_template: str
    required_model: str | None = None  # key into fetch_sample_pks()'s result, or None if no object needed


VIEW_SPECS = [
    ViewSpec("recipe_list", "/"),
    ViewSpec("recipe_detail", "/recipe/{recipe}/", "recipe"),
    ViewSpec("recipe_create", "/recipe/new/"),
    ViewSpec("recipe_update", "/recipe/{recipe}/edit/", "recipe"),
    ViewSpec("recipe_delete", "/recipe/{recipe}/delete/", "recipe"),
    ViewSpec("recipe_cooking", "/recipe/{recipe}/cook/", "recipe"),
    ViewSpec("collection_list", "/collections/"),
    ViewSpec("collection_detail", "/collections/{collection}/", "collection"),
    ViewSpec("collection_create", "/collections/new/"),
    ViewSpec("collection_update", "/collections/{collection}/edit/", "collection"),
    ViewSpec("collection_delete", "/collections/{collection}/delete/", "collection"),
    ViewSpec("meal_plan_list", "/meal-plans/"),
    ViewSpec("meal_plan_detail", "/meal-plans/{meal_plan}/", "meal_plan"),
    ViewSpec("meal_plan_create", "/meal-plans/new/"),
    ViewSpec("meal_plan_update", "/meal-plans/{meal_plan}/edit/", "meal_plan"),
    ViewSpec("meal_plan_delete", "/meal-plans/{meal_plan}/delete/", "meal_plan"),
    ViewSpec("shopping_list", "/meal-plans/{meal_plan}/shopping-list/", "meal_plan"),
    ViewSpec("jobs_list", "/jobs/"),
    ViewSpec("job_detail", "/jobs/{job}/", "job"),
    ViewSpec("settings", "/settings/"),
    ViewSpec("manage_ingredient_names", "/manage/ingredient-names/"),
    ViewSpec("manage_units", "/manage/units/"),
    ViewSpec("manage_keywords", "/manage/keywords/"),
    ViewSpec("about", "/about/"),
]


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(base_url: str, timeout: float = 15.0) -> None:
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(base_url, timeout=1)  # noqa: S310 - fixed localhost URL we just built
            return
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.3)
    raise RuntimeError(f"Server at {base_url} did not respond within {timeout}s")


def _terminate(process: subprocess.Popen[bytes]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def start_dev_server(port: int) -> subprocess.Popen[bytes]:
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings"}
    process = subprocess.Popen(  # noqa: S603 - fixed, hardcoded argv; no untrusted input
        [
            sys.executable,
            str(SRC_DIR / "manage.py"),
            "runserver",
            f"127.0.0.1:{port}",
            "--noreload",
        ],
        cwd=SRC_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_server(f"http://127.0.0.1:{port}/")
    except Exception:
        _terminate(process)
        raise
    return process


def fetch_sample_pks() -> dict[str, int | None]:
    sys.path.insert(0, str(SRC_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django

    django.setup()

    from recipes.models import AIJob, MealPlan, Recipe, RecipeCollection

    def first_pk(queryset: object) -> int | None:
        obj = queryset.first()  # type: ignore[attr-defined]
        return obj.pk if obj else None

    return {
        "recipe": first_pk(Recipe.objects.all()),
        "collection": first_pk(RecipeCollection.objects.all()),
        "meal_plan": first_pk(MealPlan.objects.all()),
        "job": first_pk(AIJob.objects.all()),
    }


def resolve_urls(sample_pks: dict[str, int | None]) -> list[tuple[str, str]]:
    resolved: list[tuple[str, str]] = []
    for spec in VIEW_SPECS:
        if spec.required_model is not None:
            pk = sample_pks.get(spec.required_model)
            if pk is None:
                logger.warning("Skipping %s: no %s rows in the database", spec.name, spec.required_model)
                continue
            path = spec.path_template.format(**{spec.required_model: pk})
        else:
            path = spec.path_template
        resolved.append((spec.name, path))
    return resolved


def capture_screenshots(base_url: str, urls: list[tuple[str, str]]) -> tuple[int, int]:
    from playwright.sync_api import sync_playwright

    captured = 0
    failed = 0

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for viewport_name, context_kwargs in VIEWPORTS.items():
                out_dir = OUTPUT_DIR / viewport_name
                out_dir.mkdir(parents=True, exist_ok=True)
                context = browser.new_context(**context_kwargs)
                page = context.new_page()
                for name, path in urls:
                    url = base_url + path
                    try:
                        page.goto(url, wait_until="networkidle", timeout=10_000)
                        page.screenshot(path=str(out_dir / f"{name}.png"), full_page=True)
                        captured += 1
                    except Exception as exc:  # one bad view shouldn't abort the run
                        logger.warning("Failed to screenshot %s (%s): %s", name, url, exc)
                        failed += 1
                context.close()
        finally:
            browser.close()

    return captured, failed


def main() -> None:
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    sample_pks = fetch_sample_pks()
    urls = resolve_urls(sample_pks)
    skipped = len(VIEW_SPECS) - len(urls)

    server = start_dev_server(port)
    try:
        captured, failed = capture_screenshots(base_url, urls)
    finally:
        _terminate(server)

    logger.info(
        "Done. %d screenshots captured, %d failed, %d views skipped (missing data). Output: %s",
        captured,
        failed,
        skipped,
        OUTPUT_DIR,
    )


if __name__ == "__main__":
    main()
