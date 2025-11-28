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
uv sync
uv run python src/plated/manage.py migrate
uv run python src/plated/manage.py runserver
```

## Documentation

Comprehensive documentation is available in the `docs/` directory.

### View Documentation Locally

``` bash
uv run mkdocs serve
```

Then open `http://localhost:8001` in your browser.

### Build Documentation

``` bash
uv run mkdocs build
```

## Technology Stack

- **Backend**: Django 5.2+
- **Database**: SQLite (PostgreSQL supported)
- **Frontend**: Bootstrap 5, vanilla JavaScript
- **PDF Generation**: Typst
- **Package Management**: uv

## Development

### Run Tests

``` bash
uv run pytest
```

### Code Quality

``` bash
# Format code
uv run ruff format src/

# Lint code
uv run ruff check src/

# Type checking
uv run mypy src/
```

## License

MIT
