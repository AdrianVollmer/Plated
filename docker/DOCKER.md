# Docker Deployment Guide

This guide explains how to deploy the Plated recipe app using Docker.

## Quick Start

1. **Clone the repository and navigate to the project directory:**
   ```bash
   cd /path/to/plated
   ```

2. **Create a `.env` file** (optional, for customization):
   ```bash
   cp docker/.env.example docker/.env
   # Edit docker/.env with your preferred settings
   ```

3. **Build and start the containers:**
   ```bash
   cd docker
   docker-compose up -d
   ```

4. **Access the application:**
   Open your browser and navigate to `http://localhost:8000`

## Environment Variables

The following environment variables can be customized in your `docker/.env` file or `docker/docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (dev key) | Django secret key. **Must be changed in production!** |
| `DEBUG` | `False` | Set to `True` for development, `False` for production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed hostnames |
| `PORT` | `8000` | Port to expose the application on the host |
| `DATABASE_PATH` | `/app/data/db.sqlite3` | Path to SQLite database inside container |
| `STATIC_ROOT` | `/app/staticfiles` | Path to static files inside container |
| `MEDIA_ROOT` | `/app/media` | Path to media files inside container |

## Volumes

The following Docker volumes are used to persist data:

- **db_data**: SQLite database
- **static_files**: Collected static files (CSS, JS, images)
- **media_files**: User-uploaded files (recipe images)

## Common Commands

**Note:** Run these commands from the `docker/` directory, or use `-f docker/docker-compose.yml` from the project root.

### View logs
```bash
docker-compose logs -f
```

### Stop the application
```bash
docker-compose down
```

### Restart the application
```bash
docker-compose restart
```

### Run management commands
```bash
# Run migrations
docker-compose exec web python src/manage.py migrate

# Create superuser
docker-compose exec web python src/manage.py createsuperuser

# Collect static files
docker-compose exec web python src/manage.py collectstatic

# Seed database with sample data
docker-compose exec web python src/manage.py seed_db
```

### Backup the database
```bash
docker-compose exec web cat /app/data/db.sqlite3 > backup.sqlite3
```

### Restore the database
```bash
cat backup.sqlite3 | docker-compose exec -T web tee /app/data/db.sqlite3 > /dev/null
docker-compose restart
```

## Production Deployment

For production deployments, consider the following:

1. **Generate a strong SECRET_KEY:**
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

2. **Set DEBUG=False** in your environment variables

3. **Configure ALLOWED_HOSTS** with your domain name(s)

4. **Use a reverse proxy** (e.g., nginx) in front of Django for better performance and security

5. **Use a production WSGI server** instead of `runserver`. Update the CMD in `docker/Dockerfile`:
   ```dockerfile
   CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--chdir", "src", "config.wsgi:application"]
   ```
   And add `gunicorn` to dependencies in `pyproject.toml`

6. **Set up regular backups** of the database and media volumes

7. **Use HTTPS** with proper SSL certificates

## Troubleshooting

### Permission errors
If you encounter permission errors with volumes, you may need to adjust permissions:
```bash
docker-compose exec web chown -R $(id -u):$(id -g) /app/data /app/media /app/staticfiles
```

### Database locked errors
If you get "database is locked" errors, ensure only one process is accessing the database, or consider using PostgreSQL for better concurrency.

### Static files not loading
Run collectstatic manually:
```bash
docker-compose exec web python src/manage.py collectstatic --noinput
docker-compose restart
```
