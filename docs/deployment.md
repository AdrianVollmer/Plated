# Deployment

Production deployment guide for Plated.

## Pre-Deployment Checklist

- [ ] Generate a strong `SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Set up HTTPS/SSL certificates
- [ ] Configure backup strategy
- [ ] Test all features in staging environment

## Security Configuration

### Generate SECRET_KEY

``` bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Store securely and set as environment variable.

### Django Settings

In production, configure these via environment variables:

``` bash
SECRET_KEY=<your-generated-secret-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

## Deployment Options

### Option 1: Docker with Reverse Proxy

Recommended for most deployments.

#### 1. Set Up Nginx

Example nginx configuration:

``` nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    client_max_body_size 10M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /path/to/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
}
```

#### 2. Use Production WSGI Server

Update `docker/Dockerfile` CMD:

``` dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--chdir", "src", "config.wsgi:application"]
```

Add to `pyproject.toml`:

``` toml
dependencies = [
    "django>=5.2.8",
    "pillow>=12.0.0",
    "requests>=2.32.5",
    "gunicorn>=23.0.0",
]
```

#### 3. Configure Docker Compose

Production `docker/docker-compose.yml`:

``` yaml
version: '3.8'

services:
  web:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    restart: always
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - db_data:/app/data
      - static_files:/app/staticfiles
      - media_files:/app/media
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=False
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - DATABASE_PATH=/app/data/db.sqlite3
      - STATIC_ROOT=/app/staticfiles
      - MEDIA_ROOT=/app/media

volumes:
  db_data:
  static_files:
  media_files:
```

### Option 2: Native Deployment

#### 1. Set Up systemd Service

Create `/etc/systemd/system/plated.service`:

``` ini
[Unit]
Description=Plated Recipe Manager
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/plated
Environment="PATH=/opt/plated/.venv/bin"
Environment="SECRET_KEY=your-secret-key"
Environment="DEBUG=False"
Environment="ALLOWED_HOSTS=yourdomain.com"
ExecStart=/opt/plated/.venv/bin/gunicorn --bind 127.0.0.1:8000 --chdir src config.wsgi:application

[Install]
WantedBy=multi-user.target
```

#### 2. Enable and Start Service

``` bash
sudo systemctl daemon-reload
sudo systemctl enable plated
sudo systemctl start plated
```

#### 3. Configure Nginx

Use the nginx configuration from Option 1.

## Database Considerations

### SQLite (Default)

Suitable for:

- Small to medium deployments
- Single-server setups
- Low to moderate traffic

Limitations:

- Limited concurrency
- No network access
- Single write operation at a time

### PostgreSQL (Production Alternative)

For high-traffic sites, consider PostgreSQL.

Update `pyproject.toml`:

``` toml
dependencies = [
    "django>=5.2.8",
    "pillow>=12.0.0",
    "requests>=2.32.5",
    "psycopg[binary]>=3.2.0",
]
```

Update settings:

``` python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```
