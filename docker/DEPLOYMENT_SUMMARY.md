# Deployment Summary

## Files Created

All Docker-related files are in the `docker/` directory:

1. **docker/Dockerfile** - Multi-stage Docker image with Python 3.12, uv, and Typst
2. **docker/docker-compose.yml** - Orchestration with volumes and environment variables
3. **docker/docker-entrypoint.sh** - Entrypoint script that runs migrations and collects static files
4. **.dockerignore** - Excludes unnecessary files from Docker image (in project root)
5. **docker/.env.example** - Template for environment variables
6. **docker/DOCKER.md** - Comprehensive deployment documentation

## Files Modified

1. **src/config/settings.py** - Updated to read from environment variables:
   - `SECRET_KEY` - Django secret key
   - `DEBUG` - Debug mode toggle
   - `ALLOWED_HOSTS` - Allowed hostnames
   - `DATABASE_PATH` - SQLite database location
   - `STATIC_ROOT` - Static files directory
   - `MEDIA_ROOT` - Media files directory

## Docker Volumes

Three persistent volumes are configured:
- **db_data** - Stores SQLite database
- **static_files** - Stores collected static assets
- **media_files** - Stores user-uploaded recipe images

## Quick Start

```bash
# Navigate to docker directory
cd docker

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Create admin user
docker-compose exec web python src/manage.py createsuperuser

# Access the app
# http://localhost:8000
```

## Environment Variables

Key variables for customization (set in `docker/.env` or `docker/docker-compose.yml`):

- `SECRET_KEY` - **MUST change in production**
- `DEBUG` - Set to `False` for production
- `ALLOWED_HOSTS` - Your domain names (comma-separated)
- `PORT` - Host port (default: 8000)

## Production Considerations

1. Generate a strong `SECRET_KEY`
2. Set `DEBUG=False`
3. Configure `ALLOWED_HOSTS` properly
4. Use a reverse proxy (nginx)
5. Consider using gunicorn instead of runserver
6. Set up regular backups
7. Use HTTPS

See `docker/DOCKER.md` for detailed instructions.
