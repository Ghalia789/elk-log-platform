# LogLens project progress

Last reviewed: 2026-11-11

## Completed

- Repository scaffold created for the Flask app, Logstash, Elasticsearch,
  Kibana, scripts, documentation, and tests.
- Docker Compose defines Elasticsearch, Kibana, Logstash, MongoDB, Redis, and
  the Flask webapp on the `elk-net` bridge network.
- Elasticsearch, MongoDB, Redis, and the webapp have healthchecks. Services
  that depend on another service wait for its healthy state.
- Persistent named volumes are configured for Elasticsearch, Logstash data,
  MongoDB, Redis, and shared uploads.
- `.env.example` documents the local configuration contract. `.env` is ignored
  by Git.
- Flask application factory implemented with `/` and `/health` routes.
- Flask image uses Python 3.11, installs dependencies before application code,
  runs Gunicorn on port 8000, and uses a non-root user.
- Faker-based SaaS log generator implemented at
  `scripts/generate_logs.py`. It emits CSV or newline-delimited JSON and
  supports weighted levels, services, HTTP statuses, and recent timestamps.
- README contains setup, environment, service, troubleshooting, and sample log
  generation instructions.

## Current limitations

- Flask routes are currently a minimal health/Hello World surface; upload,
  search, MongoDB, Redis, and Elasticsearch application integrations are not
  implemented yet.
- Logstash CSV and JSON pipelines now read the shared upload volume, parse the
  generated fields, add upload IDs, and write to `logs-saas-*`. They still
  need broader fixture coverage and an end-to-end automated test.
- `elasticsearch/index-template.json` is empty and needs the `logs-saas-*`
  index template and mappings.
- Kibana exports and dashboards have not been added.
- Automated tests are not implemented yet.

## Next implementation steps

1. Add the Logstash CSV and JSON pipelines and verify indexing into
   `logs-saas-*`.
2. Implement Flask upload handling with the required
   `<upload_id>__<original_name>` naming convention.
3. Add MongoDB metadata/search-history persistence and Redis caching/sessions.
4. Add Elasticsearch mappings, search endpoints, and focused tests.
5. Import Kibana dashboards and document the end-to-end upload-to-search flow.
