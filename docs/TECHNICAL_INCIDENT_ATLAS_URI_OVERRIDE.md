# Technical incident: Atlas URI override and startup health checks

- **Date:** 2026-11-18
- **Component:** Flask webapp, Docker Compose, MongoDB Atlas
- **Status:** Resolved
- **Severity:** Development environment configuration issue

## Symptoms

After correcting the Atlas URI in the ignored `.env` file, the health endpoint
still reported MongoDB as down:

```json
{
  "status": "degraded",
  "dependencies": {
    "mongodb": {
      "status": "down",
      "error": "Port must be an integer between 0 and 65535"
    }
  }
}
```

A request made immediately after recreating the webapp also sometimes returned:

```text
curl: (56) Recv failure: Connection reset by peer
```

## Root cause

Two independent behaviors were involved:

1. **Shell environment precedence:** Docker Compose interpolation gives an
   exported shell variable precedence over the `.env` file. The shell still
   contained an old malformed `MONGO_URI`, so `${MONGO_URI}` in
   `docker-compose.yml` injected the stale value into the new container even
   though `.env` had been corrected.
2. **Startup timing:** `docker compose up -d --force-recreate webapp` reports
   the container as started before Gunicorn has finished booting its worker and
   running the dependency checks. A curl sent immediately can therefore see a
   connection reset. This is a startup race, not an application crash.

## Diagnosis

Inspect the URI without exposing credentials:

```bash
python3 - <<'PY'
import os
from urllib.parse import urlparse
value = os.getenv("MONGO_URI")
parsed = urlparse(value or "")
print({"scheme": parsed.scheme, "host": parsed.hostname, "path": parsed.path})
PY
```

Check whether a shell override exists:

```bash
printenv MONGO_URI
```

The decisive check in this incident showed an exported shell value whose parsed
host was `ghalia`, while the corrected `.env` contained the Atlas cluster host.

## Resolution

Remove the stale shell override and recreate the webapp:

```bash
unset MONGO_URI
docker compose up -d --force-recreate webapp
```

Wait until the service is healthy, then query the endpoint:

```bash
docker compose ps webapp
curl http://localhost:8000/health
```

The resolved response was:

```json
{
  "status": "healthy",
  "dependencies": {
    "elasticsearch": {"status": "up"},
    "mongodb": {"status": "up"},
    "redis": {"status": "up"}
  }
}
```

The startup logs also confirmed that the MongoDB indexes were created:

```text
MongoDB indexes ready: files(uploaded_at, status), searches(executed_at)
```

## Prevention

- Do not export `MONGO_URI` in the shell unless intentionally overriding `.env`.
- If it was exported temporarily, run `unset MONGO_URI` before using Compose.
- Keep real Atlas credentials only in the ignored `.env` file.
- After recreating the webapp, use `docker compose ps webapp` and wait for
  `healthy` before running health requests.
- Use `docker compose logs webapp --tail 50` when the dependency status is
  `degraded`; the application is designed to start even when MongoDB is down.
