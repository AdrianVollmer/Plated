# Plated

**Modern recipe management for your kitchen.**

A Django-based web application for organizing, creating, and managing
recipes with a beautiful, mobile-friendly interface.

## Features

- Recipe management with ingredients, steps, and images
- Collections to organize related recipes
- Smart autocomplete for consistent ingredient names and units
- Import/export recipes in JSON format
- PDF generation using Typst
- AI-powered recipe extraction from URLs
- Multiple color themes including dark mode
- Meal planning and shopping lists
- Mobile-responsive design

## Quick Start

### Docker (Recommended)

``` bash
git clone https://github.com/AdrianVollmer/Plated.git
cd Plated
docker-compose up -d
```

Access at `http://localhost:8000`

### Native Installation

``` bash
git clone https://github.com/AdrianVollmer/Plated.git
cd Plated
just sync
uv run python src/plated/manage.py migrate
uv run python src/plated/manage.py runserver
```

This project uses [`just`](https://github.com/casey/just) as a task runner for common
development tasks. Run `just --list` to see all available recipes.

## Documentation

Comprehensive documentation is available in the `docs/` directory.

### View Documentation Locally

``` bash
just docs
```

Then open `http://localhost:8001` in your browser.

### Build Documentation

``` bash
just docs-build
```

## Technology Stack

- **Backend**: Django 5.2+
- **Database**: SQLite (PostgreSQL supported)
- **Frontend**: Bootstrap 5, vanilla JavaScript
- **PDF Generation**: Typst
- **Package Management**: uv

## Development

Common development tasks are wrapped in the [`justfile`](justfile). Run `just --list` to see
every recipe; the most useful ones:

| Command | Description |
| --- | --- |
| `just sync` | Install/sync dependencies |
| `just test` | Run the test suite |
| `just check` | Lint, type-check, and verify formatting (no modifications) |
| `just lint` | Lint with ruff (`just lint --fix` to auto-fix) |
| `just fmt` | Format code with ruff |
| `just fmt-check` | Check formatting without modifying files |
| `just typecheck` | Type-check with mypy |
| `just hooks-install` | Install git hooks so checks run automatically on commit |
| `just screenshots` | Seed dev data and screenshot every view at mobile/desktop viewports |
| `just docs` | Serve documentation locally with live reload |
| `just docs-build` | Build the static docs site |
| `just build` | Build the sdist and wheel |
| `just bump [major\|minor\|patch]` | Tag the next release and move the `latest` branch to it |
| `just run <args>` | Run the `plated` CLI |
| `just ci` | Full check: everything CI runs |

After cloning, run `just hooks-install` once so lint/format/type checks run automatically on
commit.

## License

MIT
