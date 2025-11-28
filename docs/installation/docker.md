# Docker Installation

Run Plated using Docker and Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/plated.git
cd plated
```

### 2. Build and Start

```bash
cd docker
docker-compose up -d
```

The application will be available at `http://localhost:8000`

### 3. Create Admin User

```bash
docker-compose exec web python src/manage.py createsuperuser
```

## Configuration

### Environment Variables

Customize settings in `docker/docker-compose.yml` or create `docker/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (dev key) | **Change in production!** |
| `DEBUG` | `False` | Enable debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed hostnames |
| `PORT` | `8000` | Host port mapping |
| `DATABASE_URL` | `sqlite:////app/data/db.sqlite3` | Database URL (SQLite or PostgreSQL) |
| `STATIC_ROOT` | `/app/staticfiles` | Static files directory |
| `MEDIA_ROOT` | `/app/media` | Media uploads directory |

### Example .env File

```bash
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=example.com,www.example.com
PORT=8000
```

## Data Persistence

Three Docker volumes persist your data:

- **db_data** - SQLite database
- **static_files** - CSS, JavaScript, images
- **media_files** - User-uploaded recipe images

## Common Commands

### View Logs

```bash
docker-compose logs -f
```

### Stop Application

```bash
docker-compose down
```

### Restart Application

```bash
docker-compose restart
```

### Run Management Commands

```bash
# Run migrations
docker-compose exec web python src/manage.py migrate

# Collect static files
docker-compose exec web python src/manage.py collectstatic

# Seed sample data
docker-compose exec web python src/manage.py seed_db
```

### Backup Database

```bash
docker-compose exec web cat /app/data/db.sqlite3 > backup.sqlite3
```

### Restore Database

```bash
cat backup.sqlite3 | docker-compose exec -T web tee /app/data/db.sqlite3 > /dev/null
docker-compose restart
```

## Docker Image Details

The Dockerfile includes:

- Python 3.12 slim base image
- uv package manager
- Typst for PDF generation
- All Python dependencies
- Automatic migrations on startup

## Updating

### Pull Latest Changes

```bash
git pull origin main
cd docker
docker-compose build --no-cache
docker-compose up -d
```

### Run Migrations After Update

```bash
docker-compose exec web python src/manage.py migrate
```

## Troubleshooting

### Permission Errors

```bash
docker-compose exec web chown -R $(id -u):$(id -g) /app/data /app/media /app/staticfiles
```

### Database Locked

SQLite has limited concurrency. Consider PostgreSQL for high-traffic deployments.

### Static Files Not Loading

```bash
docker-compose exec web python src/manage.py collectstatic --noinput
docker-compose restart
```

### Container Won't Start

Check logs for errors:

```bash
docker-compose logs web
```

## Next Steps

- See [Deployment](../deployment.md) for production configuration
- See the [detailed Docker guide](../../docker/DOCKER.md) for advanced topics
