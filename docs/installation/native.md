# Native Installation

Install Plated directly on your system using Python and uv.

## Prerequisites

- Python 3.12 or later
- [uv](https://github.com/astral-sh/uv) package manager
- [Typst](https://github.com/typst/typst) (optional, for PDF generation)

### Installing uv

=== "macOS/Linux"
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"
    ```powershell
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

### Installing Typst

=== "macOS"
    ```bash
    brew install typst
    ```

=== "Linux"
    ```bash
    # Download latest release from GitHub
    curl -LO https://github.com/typst/typst/releases/latest/download/typst-x86_64-unknown-linux-musl.tar.xz
    tar -xf typst-x86_64-unknown-linux-musl.tar.xz
    sudo mv typst-*/typst /usr/local/bin/
    ```

=== "Windows"
    ```powershell
    # Download from https://github.com/typst/typst/releases
    # Extract and add to PATH
    ```

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/plated.git
cd plated
```

### 2. Install Dependencies

```bash
uv sync
```

This creates a virtual environment and installs all required packages.

### 3. Run Migrations

```bash
uv run python src/manage.py migrate
```

### 4. Create Static Directories

```bash
mkdir -p src/media src/staticfiles src/logs
```

### 5. Collect Static Files

```bash
uv run python src/manage.py collectstatic --noinput
```

### 6. Create Admin User

```bash
uv run python src/manage.py createsuperuser
```

Follow the prompts to set username, email, and password.

### 7. Start Development Server

```bash
uv run python src/manage.py runserver
```

Access the application at `http://localhost:8000`

## Optional: Seed Sample Data

```bash
uv run python src/manage.py seed_db
```

## Development Tools

### Run Tests

```bash
uv run pytest
```

### Type Checking

```bash
uv run mypy src/
```

### Code Formatting

```bash
# Check formatting
uv run ruff format --check src/

# Apply formatting
uv run ruff format src/
```

### Linting

```bash
uv run ruff check src/
```

## Configuration

### Environment Variables

Create a `.env` file in the project root (optional):

```bash
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database configuration (SQLite by default)
DATABASE_URL=sqlite:///path/to/db.sqlite3

# Or for PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/plated

STATIC_ROOT=/path/to/staticfiles
MEDIA_ROOT=/path/to/media
```

See [settings.py](../src/config/settings.py) for all available options.

**Note:** The old `DATABASE_PATH` variable is still supported for backward compatibility, but `DATABASE_URL` is preferred.

## Troubleshooting

### Port Already in Use

Run on a different port:

```bash
uv run python src/manage.py runserver 8080
```

### Static Files Not Loading

Ensure you've run `collectstatic`:

```bash
uv run python src/manage.py collectstatic --noinput
```

### Database Locked

Only one process can access SQLite at a time. Stop other instances or use a different database for production.

## Next Steps

- See [Deployment](../deployment.md) for production setup
- See [Features](../features.md) for usage guide
