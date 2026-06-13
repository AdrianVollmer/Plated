FROM python:3.12-slim

ARG VERSION=0.0.0

# Install system dependencies, nginx, and Typst
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    xz-utils \
    nginx \
    && curl -fsSL https://github.com/typst/typst/releases/download/v0.14.0/typst-x86_64-unknown-linux-musl.tar.xz \
    | tar -xJ -C /usr/local/bin --strip-components=1 typst-x86_64-unknown-linux-musl/typst \
    && apt-get purge -y curl xz-utils \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# hatch-vcs reads this env var when no git repo is present
ENV SETUPTOOLS_SCM_PRETEND_VERSION=$VERSION

RUN python -m venv .venv && \
    . /app/.venv/bin/activate && \
    pip install gunicorn .

# Create directories for volumes
RUN mkdir -p /app/data /app/staticfiles /app/media

# Configure nginx
RUN rm -f /etc/nginx/sites-enabled/default && \
    mkdir -p /var/log/nginx /var/lib/nginx

RUN echo 'upstream django {\n\
    server 127.0.0.1:8000;\n\
}\n\
\n\
server {\n\
    listen 80;\n\
    server_name _;\n\
    client_max_body_size 20M;\n\
\n\
    location /static/ {\n\
        alias /app/staticfiles/;\n\
        expires 30d;\n\
        add_header Cache-Control "public, immutable";\n\
    }\n\
\n\
    location /media/ {\n\
        alias /app/media/;\n\
        expires 7d;\n\
        add_header Cache-Control "public";\n\
    }\n\
\n\
    location / {\n\
        proxy_pass http://django;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_set_header X-Forwarded-Proto $scheme;\n\
        proxy_redirect off;\n\
    }\n\
}\n' > /etc/nginx/sites-available/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

RUN echo '#!/bin/bash\n\
set -e\n\
\n\
cd /app/src/plated\n\
. /app/.venv/bin/activate\n\
\n\
echo "Running database migrations..."\n\
/app/.venv/bin/python manage.py migrate --noinput\n\
\n\
echo "Collecting static files..."\n\
/app/.venv/bin/python manage.py collectstatic --noinput\n\
\n\
echo "Starting nginx..."\n\
nginx\n\
\n\
echo "Starting gunicorn..."\n\
exec /app/.venv/bin/gunicorn config.wsgi --bind 127.0.0.1:8000\n' > /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
