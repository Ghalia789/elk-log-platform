# LogLens project progress

Last reviewed: 2026-11-18

## Completed

- Repository scaffold created for the Flask app, Logstash, Elasticsearch,
  Kibana, scripts, documentation, and tests.
- Docker Compose defines Elasticsearch, Kibana, Logstash, Redis, and the Flask
  webapp on the `elk-net` bridge network. MongoDB 7 remains available through
  the optional `local-mongo` profile.
- Elasticsearch, Redis, and the webapp have healthchecks in the default Atlas
  mode. The local MongoDB profile also has a MongoDB healthcheck.
- Persistent named volumes are configured for Elasticsearch, Logstash data,
  local MongoDB, Redis, and shared uploads.
- `.env.example` documents the Atlas configuration by default and the optional
  local MongoDB profile. `.env` is ignored by Git.
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
  search, MongoDB Atlas, Redis, and Elasticsearch application integrations are
  not implemented yet.
- Logstash CSV and JSON pipelines now read the shared upload volume, parse the
  generated fields, add upload IDs, and write to `logs-saas-*`. They still
  need broader fixture coverage and an end-to-end automated test.
- `elasticsearch/index-template.json` defines the `logs-saas-*` data-stream
  template with one shard, zero replicas, and the log field mappings. Existing
  backing indices keep their original mappings; new backing indices use this
  template.
- Kibana exports and dashboards have not been added.
- Automated tests are not implemented yet.

## Next implementation steps

1. Implement Flask upload handling with the required
   `<upload_id>__<original_name>` naming convention.
2. Add MongoDB Atlas metadata/search-history persistence and Redis
  caching/sessions.
3. Add Elasticsearch mappings, search endpoints, and focused tests.
4. Import Kibana dashboards and document the end-to-end upload-to-search flow.
