# Deployment

How to run the platform in production — environment configuration, infrastructure requirements, migration strategy, and operational concerns.

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `<secret_key>` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@host:5432/dbname` |
| `REDIS_URL` | Redis connection string | `redis://host:6379/0` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames | `api.example.com` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `ACCESS_TOKEN_LIFETIME_MINUTES` | JWT access token lifetime | `30` |
| `REFRESH_TOKEN_LIFETIME_DAYS` | JWT refresh token lifetime | `7` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed origins | (none) |

---

## Infrastructure Requirements

| Service | Version | Notes |
|---------|---------|-------|
| PostgreSQL | 16+ | Primary database |
| Redis | 7+ | Cache and token blacklist backend |
| Python | 3.14+ | Application runtime |

### Minimum Resources (per instance)

| Resource | Recommendation |
|----------|---------------|
| CPU | 1 vCPU |
| Memory | 512 MB |
| Disk | Minimal (stateless app) |

---

## Production Server

Use Gunicorn with ASGI (uvicorn workers) or WSGI:

```bash
# WSGI
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4

# ASGI
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --workers 4
```

---

## Docker

The project includes a single-stage Dockerfile for containerized deployment:

```bash
docker compose up -d   # Starts PostgreSQL, Redis, and the app
```

The app service uses Gunicorn bound to port 8000.

---

## Database Migrations

### Running in Production

```bash
uv run python manage.py migrate --no-input
```

### Zero-Downtime Strategy

1. Migrations must be backward-compatible with the currently running code
2. Destructive changes (column removal, rename) require a two-phase approach:
   - Phase 1: Deploy code that no longer uses the column
   - Phase 2: Run migration that removes the column
3. Always test migrations against a copy of production data before applying

---

## Static Files

In production, static files are collected and served by a reverse proxy (nginx) or object storage (S3):

```bash
uv run python manage.py collectstatic --no-input
```

Do not serve static files through Django/Gunicorn in production.

---

## Scaling Considerations

- The application is stateless — scale horizontally by adding instances
- Session state lives in JWT tokens (no sticky sessions required)
- Database connection pooling (PgBouncer) recommended at 10+ instances
- Redis is used for cache and token blacklist — single instance sufficient for moderate load
