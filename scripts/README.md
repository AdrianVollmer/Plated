# Scripts

## `screenshot_views.py`

Seeds-aware visual sweep: starts a dev server, screenshots every view at mobile and desktop
viewports, writes PNGs to `screenshots/<mobile|desktop>/<name>.png`.

One-time setup (per machine — this downloads the actual browser binary, separate from `uv sync`):

```
uv run playwright install chromium
```

Usage:

```
uv run python src/plated/recipes/management/commands/seed_testdata.py  # seed dev data
uv run scripts/screenshot_views.py
```

Or via `just screenshots`, which does both steps.
