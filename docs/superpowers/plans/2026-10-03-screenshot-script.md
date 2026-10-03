# Mobile Screenshot Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a developer script that screenshots every view in the app at mobile and desktop
viewports, backed by seeded test data that includes recipes with varied image counts/aspect
ratios, so mobile layout defects can be spotted by eye.

**Architecture:** `seed_testdata.py` gains a Pillow-based placeholder-image generator and
assigns 0/1/2/4 images (cycling aspect ratios) across the 30 `[TEST]` recipes it creates.
`scripts/screenshot_views.py` starts a `manage.py runserver` subprocess, queries sample pks via
the Django ORM, drives headless Chromium via Playwright at two viewport sizes, and writes PNGs
to `screenshots/<mobile|desktop>/<name>.png`, skipping (with a warning) any view whose required
object doesn't exist.

**Tech Stack:** Python, Django ORM (via `django.setup()`), Pillow (already a dependency),
Playwright (new dev dependency).

**Spec:** `docs/superpowers/specs/2026-10-03-screenshot-script-design.md`

---

### Task 1: Add Playwright dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add the dependency**

In `pyproject.toml`, in the `[dependency-groups]` `dev` list, add `"playwright>=1.49.0",`
alphabetically (after `"pre-commit>=4.4.0",`, before `"pytest>=9.0.1",`):

```toml
dev = [
    "django-stubs>=5.2.7",
    "djlint>=1.39.2",
    "hatch>=1.15.1",
    "hatch-vcs>=0.5.0",
    "mkdocs-material>=9.7.0",
    "mypy>=1.18.2",
    "playwright>=1.49.0",
    "pre-commit>=4.4.0",
    "pytest>=9.0.1",
    "pytest-django>=4.11.1",
    "ruff>=0.14.5",
    "ty>=0.0.84",
    "types-requests>=2.32.4.20250913",
]
```

- [ ] **Step 2: Sync dependencies and install the browser**

Run: `uv sync`
Expected: completes without error, `playwright` now in `uv.lock`.

Run: `uv run playwright install chromium`
Expected: downloads and installs the Chromium browser used by Playwright (one-time setup; not
triggered automatically by the script).

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit --author "Adrian Vollmer <5rx@mailbox.org>" -m "build: add playwright dev dependency for screenshot tooling"
```

---

### Task 2: Generate placeholder images in `seed_testdata.py`

**Files:**
- Modify: `src/plated/recipes/management/commands/seed_testdata.py`

This adds an image-generation helper and wires it into the existing per-recipe loop. No test
suite covers `seed_testdata.py` today (it's a standalone data-seeding script, not app behavior),
so this task is verified by running the command and inspecting the DB/media directory directly
rather than by a pytest test — consistent with the rest of that file.

- [ ] **Step 1: Add imports needed for image generation**

At the top of `src/plated/recipes/management/commands/seed_testdata.py`, after the existing
`from pathlib import Path` line, add:

```python
from io import BytesIO
```

After the `django.setup()` call and before the `from recipes.management.commands.testviews
import (...)` block, add:

```python
from django.core.files.base import ContentFile  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
```

Then update the existing model import to include `RecipeImage`:

```python
from recipes.models import (  # noqa: E402
    AISettings,
    Ingredient,
    MealPlan,
    MealPlanEntry,
    Recipe,
    RecipeCollection,
    RecipeImage,
    Step,
)
```

- [ ] **Step 2: Add the placeholder-image helper function**

Add this function after the imports, before `def seed_test_data() -> None:`:

```python
# (width, height) pairs covering the aspect ratios views need to handle.
PLACEHOLDER_IMAGE_SIZES = [
    (800, 600),  # landscape 4:3
    (600, 800),  # portrait 3:4
    (700, 700),  # square 1:1
    (960, 540),  # wide 16:9
]


def _placeholder_color(label: str) -> tuple[int, int, int]:
    """Derive a stable, visually distinct color from a label string."""
    digest = sum(ord(c) for c in label)
    return (80 + (digest * 37) % 150, 80 + (digest * 59) % 150, 80 + (digest * 83) % 150)


def _generate_placeholder_image(label: str, size: tuple[int, int]) -> ContentFile:
    """Create an in-memory JPEG with a solid color and centered label text."""
    image = Image.new("RGB", size, color=_placeholder_color(label))
    draw = ImageDraw.Draw(image)
    text_width, text_height = draw.textbbox((0, 0), label)[2:]
    position = ((size[0] - text_width) / 2, (size[1] - text_height) / 2)
    draw.text(position, label, fill=(255, 255, 255))

    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return ContentFile(buffer.getvalue(), name=f"{label.replace(' ', '_')}.jpg")
```

- [ ] **Step 3: Assign images per recipe in the create loop**

In `seed_test_data()`, find the loop that creates recipes (`for i in range(30):`). Right after
the `recipes.append(recipe)` line (still inside the `for i in range(30):` loop body), add:

```python
        # Assign a varied image set: no images, one, two, or four, cycling aspect ratios.
        image_count = {0: 0, 1: 1, 2: 2, 3: 4}[i % 4]
        for j in range(image_count):
            size = PLACEHOLDER_IMAGE_SIZES[j % len(PLACEHOLDER_IMAGE_SIZES)]
            label = f"Recipe {i + 1} - Image {j + 1}"
            RecipeImage.objects.create(
                recipe=recipe,
                image=_generate_placeholder_image(label, size),
                order=j,
                caption=label,
            )
```

- [ ] **Step 4: Run the seed command and verify images were created**

Run: `uv run python src/plated/manage.py seed_testdata`
Expected: prints `Test data created successfully` with no traceback.

Run:
```bash
uv run python src/plated/manage.py shell -c "
from recipes.models import Recipe, RecipeImage
recipes = Recipe.objects.filter(title__startswith='[TEST]').order_by('id')
counts = [r.images.count() for r in recipes]
print(counts[:8])
print('total images:', RecipeImage.objects.count())
"
```
Expected: the first 8 counts show the `[0, 1, 2, 4]` cycle repeating (e.g. `[0, 1, 2, 4, 0, 1, 2,
4]`), and `total images` is `30 // 4 * (0+1+2+4) + remainder` — just confirm it's greater than 0
and matches the cycle (for 30 recipes: i%4 counts are 0,1,2,4 repeating → 7 or 8 of each value;
total = 7*0 + 8*1 + 7*2 + 8*4 = 54, order may shift by one depending on which remainder index 30
lands on, so just confirm the printed counts follow the `0,1,2,4` repeating pattern).

- [ ] **Step 5: Commit**

```bash
git add src/plated/recipes/management/commands/seed_testdata.py
git commit --author "Adrian Vollmer <5rx@mailbox.org>" -m "feat: seed test recipes with varied placeholder images

So screenshot/visual review covers the no-image, single-image, and
carousel (multi-image, mixed aspect ratio) states, not just text-only
recipes."
```

---

### Task 3: Write `scripts/screenshot_views.py`

**Files:**
- Create: `scripts/screenshot_views.py`
- Modify: `.gitignore`

- [ ] **Step 1: Add `screenshots/` to `.gitignore`**

Append to `.gitignore`:

```
screenshots/
```

- [ ] **Step 2: Create the script**

Create `scripts/screenshot_views.py`:

```python
"""Screenshot every view in the app at mobile and desktop viewports.

Run against an already-seeded dev database (see `manage.py seed_testdata`).
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

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("screenshot_views")

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src" / "plated"
OUTPUT_DIR = REPO_ROOT / "screenshots"

VIEWPORTS = {
    "mobile": {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 2, "is_mobile": True},
    "desktop": {"viewport": {"width": 1440, "height": 900}},
}


@dataclass(frozen=True)
class ViewSpec:
    name: str
    path_template: str
    required_model: str | None = None  # key into SamplePks, or None if no object needed


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
            urllib.request.urlopen(base_url, timeout=1)
            return
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.3)
    raise RuntimeError(f"Server at {base_url} did not respond within {timeout}s")


def start_dev_server(port: int) -> subprocess.Popen[bytes]:
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings"}
    process = subprocess.Popen(
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
        process.terminate()
        process.wait(timeout=5)
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
                    except Exception as exc:  # noqa: BLE001 - one bad view shouldn't abort the run
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
        server.terminate()
        server.wait(timeout=5)

    logger.info(
        "Done. %d screenshots captured, %d failed, %d views skipped (missing data). Output: %s",
        captured,
        failed,
        skipped,
        OUTPUT_DIR,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Make sure the DB is seeded, then run the script**

Run: `uv run python src/plated/manage.py seed_testdata`
Expected: `Test data created successfully`

Run: `uv run scripts/screenshot_views.py`
Expected: log lines ending with a `Done. N screenshots captured, 0 failed, 0 views skipped...`
summary (0 failed/skipped assuming the seed command above ran and created at least one of each
model). `screenshots/mobile/` and `screenshots/desktop/` each contain one PNG per view in
`VIEW_SPECS` (24 views × 2 viewports = 48 files).

- [ ] **Step 4: Spot-check image variants show up**

Open `screenshots/mobile/recipe_list.png` and `screenshots/desktop/recipe_list.png` (e.g. via the
Read tool, since they're images) and confirm the recipe cards show a visible mix of: no-image
placeholders, single images, and multi-image indicators, matching the 0/1/2/4 distribution from
Task 2.

- [ ] **Step 5: Commit**

```bash
git add scripts/screenshot_views.py .gitignore
git commit --author "Adrian Vollmer <5rx@mailbox.org>" -m "feat: add mobile/desktop screenshot script for visual review

Walks every view and screenshots it at mobile and desktop viewports
so layout regressions (especially mobile ones) can be caught by eye
instead of by clicking through the app manually."
```

---

### Task 4: Manual end-to-end check

**Files:** none (verification only)

- [ ] **Step 1: Fresh run from a clean checkout state**

Run:
```bash
rm -rf screenshots
uv run python src/plated/manage.py seed_testdata
uv run scripts/screenshot_views.py
```
Expected: completes with `0 failed, 0 views skipped`, `screenshots/` repopulated.

- [ ] **Step 2: Review a sample of mobile screenshots for the originally reported aesthetic issues**

Open a handful of `screenshots/mobile/*.png` (recipe_detail, recipe_create, recipe_update,
collection_detail, meal_plan_detail, jobs_list) and visually confirm there's nothing obviously
broken (overflow, unreadable text, misaligned carousel) — this is the actual payoff of the
script and worth doing once by hand to confirm the tool is useful.

- [ ] **Step 3: Confirm `uv run ty` and `uv run ruff check` are still clean on touched files**

Run: `uv run ruff check scripts/screenshot_views.py src/plated/recipes/management/commands/seed_testdata.py`
Expected: no errors (fix any lint issues found before moving on).

No commit for this task — it's verification only.
