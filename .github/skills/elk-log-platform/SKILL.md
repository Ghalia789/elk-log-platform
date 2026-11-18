---
name: elk-log-platform
description: "Work on the LogLens ELK platform. Use for Docker Compose, Flask uploads and APIs, Swagger/OpenAPI, Logstash pipelines, Elasticsearch templates, MongoDB, Redis, and end-to-end log ingestion."
---

# LogLens ELK Platform

## Project Conventions

- Use Docker Compose for integration work; the webapp runs on Flask and Gunicorn.
- Keep CSV, JSON, and TXT validation in `webapp/app/services/validation.py`.
- Register Flask routes through blueprints in `webapp/app/routes/`.
- Document public HTTP APIs with Swagger/OpenAPI docstrings and expose Swagger UI at `/apidocs/`.
- Keep secrets in `.env`; never commit credentials or MongoDB Atlas URIs.
- Preserve the shared upload contract: `<upload_id>__<original_name>` inside `/uploads`.
- Add focused tests for route behavior, validation, and dependency health changes.

## Validation Workflow

1. Compile Python files with `python3 -m compileall webapp/app webapp/scripts 2>/dev/null || python3 -m compileall webapp/app scripts`.
2. Start or recreate the stack with `docker compose up -d --build`.
3. Check service health with `docker compose ps`.
4. Verify the API through `/health`, `/apidocs/`, `/upload/preview`, and `/upload`.
5. Confirm Elasticsearch documents under `logs-saas-*` after Logstash processes an upload.

## Swagger/OpenAPI

- Add or update route docstrings when endpoint parameters, responses, or media types change.
- Keep examples realistic and avoid exposing filesystem paths or credentials.
- Test both the Swagger UI and generated OpenAPI JSON/spec endpoint.
- When changing `/upload`, document multipart `file` parameters and validation error responses.
