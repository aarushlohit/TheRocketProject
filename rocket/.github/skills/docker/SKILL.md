---
name: docker
description: 'Build, run, and manage Docker containers — Dockerfile best practices, docker-compose, multi-stage builds, networking, volumes. Use when: Docker, container, Dockerfile, docker-compose, containerize, Docker image, Docker container.'
---

# Docker

Containerization best practices.

## Dockerfile Best Practices

```dockerfile
# 1. Use specific base image tags (not `latest`)
FROM python:3.12-slim-bookworm

# 2. Set working directory
WORKDIR /app

# 3. Copy dependency files first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy application code last
COPY . .

# 5. Use non-root user
RUN useradd --create-home appuser
USER appuser

# 6. Define metadata
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/health || exit 1
CMD ["python", "app.py"]
```

## Multi-Stage Builds

```dockerfile
# Build stage
FROM node:20 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Docker Compose

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/app
    depends_on:
      - db
    volumes:
      - .:/app
  db:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=app
      - POSTGRES_PASSWORD=password

volumes:
  pgdata:
```

## Principles

- One process per container.
- Use `.dockerignore` to exclude `node_modules`, `.git`, `__pycache__`.
- Keep images small: use slim/alpine base images, multi-stage builds.
- Never store secrets in images — use secrets mounting or env vars at runtime.
