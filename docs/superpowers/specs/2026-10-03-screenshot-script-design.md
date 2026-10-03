# Screenshot Script Design

Date: 2026-10-03

## Overview

Add `scripts/screenshot_views.py`, a developer tool that walks every view in the app and
captures a screenshot of each at both mobile and desktop viewport widths, so visual/layout
defects (particularly on mobile) can be spotted quickly without manually clicking through the
app. It runs against the existing dev DB seeded via `seed_testdata`, which is extended to
generate dummy recipe images in several variants (none, one, many; multiple aspect ratios) so
image-heavy views (cards, carousels) are exercised too.

## Dependencies

Add `playwright` to the `dev` dependency group in `pyproject.toml`. Document in the script's
module docstring (and a short README note in `scripts/`) that `uv run playwright install
chromium` must be run once after installing dependencies — the script does not trigger browser
downloads itself, to avoid surprise network access on every run.

## Dummy Image Generation (`seed_testdata.py`)

Extend the existing `seed_test_data()` function in
`src/plated/recipes/management/commands/seed_testdata.py`:

- Add a helper `_generate_placeholder_image(label: str, size: tuple[int, int]) -> ContentFile`
  that uses Pillow to draw a solid-color JPEG with the given label text centered on it (color
  derived from a hash of the label so different images are visually distinguishable), returned
  as a `django.core.files.base.ContentFile` ready to assign to an `ImageField`.
- Four fixed aspect ratios, reused by cycling through them: landscape 4:3 (800x600), portrait 3:4
  (600x800), square 1:1 (700x700), wide 16:9 (960x540).
- After creating each of the 30 `[TEST]` recipes, assign images based on `i % 4`:
  - `i % 4 == 0`: no images (tests the no-image placeholder state in cards/detail/carousel)
  - `i % 4 == 1`: exactly one image, aspect ratio cycling across these recipes
  - `i % 4 == 2`: two images, two different aspect ratios (minimal carousel case)
  - `i % 4 == 3`: four images, all four aspect ratios (full carousel case)
- Label each image `f"Recipe {i + 1} - Image {j + 1}"` and set `order=j`.
- At the top of `seed_test_data()`, where existing `[TEST]` rows are deleted before recreation,
  no extra cleanup is needed for images: `RecipeImage` cascades on `Recipe` deletion.
- Files are written under the real `MEDIA_ROOT` via the normal `ImageField` save path (same as
  user uploads) — no special-casing for test data.

## Views Covered

Built as a static list of `(name, path_template, required_model)` in the script, derived from
`recipes/urls.py`. `required_model` says which model must have at least one row for the view to
be resolvable (`None` for views needing no object); the script fetches one `pk` per model
up front (`Recipe`, `RecipeCollection`, `MealPlan`, `MealPlanEntry`, `AIJob`) and skips entries
whose model has no rows, logging a warning.

Covered views: recipe list, recipe detail, recipe create, recipe update, recipe cooking view,
collection list, collection detail, collection create, collection update, meal plan list, meal
plan detail, meal plan create, meal plan update, shopping list, jobs list, job detail, settings,
manage ingredient names, manage units, manage keywords, about. Delete confirmation views
(`recipe_delete`, `collection_delete`, `meal_plan_delete`) are included as GET-only page loads —
the script never submits the confirmation form, so nothing is destroyed. Pure API/action
endpoints (export, PDF download, autocomplete APIs, add/remove meal entry, etc.) are excluded —
they return files or require POST/non-HTML responses, not pages to screenshot.

## Script Flow

1. Resolve a free local TCP port.
2. Launch `uv run python src/plated/manage.py runserver 127.0.0.1:<port> --noreload` as a
   subprocess, with output redirected so it doesn't clutter the terminal; poll
   `http://127.0.0.1:<port>/` until it responds (timeout ~15s) before proceeding.
3. Set up Django (`django.setup()`, same pattern as `seed_testdata.py`) to query sample `pk`s
   directly via the ORM against the configured dev DB.
4. Build the resolved list of `(name, url)` pairs, skipping and warning on any view whose
   required model has no rows.
5. Launch Playwright Chromium (headless), open two browser contexts: mobile (390x844,
   `device_scale_factor=2`, mobile UA) and desktop (1440x900).
6. For each `(name, url)` pair, for each context: navigate, wait for `networkidle`, screenshot
   full-page to `screenshots/<mobile|desktop>/<name>.png`. On any exception (404, timeout, JS
   error), log a warning with the URL and continue — one failing view does not abort the run.
7. In a `finally` block: close browser contexts/browser, terminate the `runserver` subprocess.
8. Print a short summary at the end: counts of screenshots captured vs. views skipped/failed.

## Output

`screenshots/` directory at repo root, created if missing, added to `.gitignore`. Subfolders
`mobile/` and `desktop/`, PNG files named after the view (e.g. `recipe_detail.png`,
`recipe_update.png`). Re-running overwrites existing files, so it's always a fresh snapshot of
current state.

## Error Handling Summary

- Missing sample data for a model → skip dependent views, warn, continue.
- Per-view navigation/screenshot failure → skip that view, warn, continue.
- Server fails to start → hard fail with a clear error (nothing to screenshot).
- Always clean up the server subprocess and browser, even on failure (`try`/`finally`).

## Testing

This is a developer visual-inspection tool, not application behavior — no automated test suite
coverage is added for it. The `seed_testdata.py` image generation is exercised simply by running
the seed command and confirming images appear (manual verification), consistent with how the
rest of that file already has no test coverage.

## Out of Scope

- CI integration (no headless browser in CI for this).
- Authentication handling (the app has none).
- Visual diffing/regression detection — this produces screenshots for human review, not
  pixel-diff assertions.
