# LogLens testing history

Last reviewed: 2026-11-18

This document records the verification performed during the infrastructure,
Flask, Logstash, Elasticsearch, Atlas, and upload work.

## Compose and environment

- `docker compose config` and `docker compose config --quiet` passed repeatedly
  after Compose changes.
- Default service profile was verified to include Elasticsearch, Redis, Kibana,
  Logstash, and webapp.
- The optional `local-mongo` profile was verified to add MongoDB 7.
- `.env` was confirmed ignored by Git.
- The webapp Compose environment was verified to receive `ES_HOST`, `MONGO_URI`,
  `MONGO_DB`, `REDIS_URL`, and `LOG_LEVEL`.

## Images, storage, and runtime

- The host initially reached 97% disk usage with 1.7 GB free. Docker image and
  build-cache cleanup reduced usage to 73% with 13 GB free.
- Obsolete Flask and ELK 8.15.0 images were removed. Current ELK 8.15.3
  images and LogLens volumes were preserved.
- Elasticsearch, Kibana, Redis, Logstash, and webapp were observed running.
- Elasticsearch changed from red to yellow after storage cleanup. Yellow is
  expected for a single-node cluster with unassigned replicas.
- MongoDB 7 was confirmed incompatible with the VM because AVX is not exposed;
  MongoDB Atlas became the default backend.

## Flask application

- Python compilation passed for the factory, clients, routes, upload route, and
  validation service.
- The webapp image built successfully with Python 3.11, required packages,
  Gunicorn, and a non-root `app` user.
- The factory was verified to start while dependencies were unavailable.
- `/health` was verified to return `healthy` when Elasticsearch, MongoDB Atlas,
  and Redis were reachable.
- `/health` was verified to return `degraded` while MongoDB was unavailable,
  without stopping the Flask process.
- MongoDB startup checks and index creation were verified in logs:

```text
MongoDB indexes ready: files(uploaded_at, status), searches(executed_at)
```

## Upload validation and routes

The Flask test client verified:

- `GET /upload` returns the upload form.
- CSV preview returns parsed rows without saving a file.
- Valid uploads return HTTP 202.
- Filenames are sanitized with `secure_filename`.
- Invalid extensions return HTTP 415.
- Invalid CSV rows return HTTP 400.
- Upload size limits and JSON error responses are configured.
- Temporary `.part` files are renamed atomically after writing.
- Upload logging includes upload ID, filename, size, format, and path.

## Logstash pipelines

- Initial validation found the unsupported CSV setting:

```text
Unknown setting 'tag_on_failure' for csv
```

- Removing that setting fixed the issue because the CSV plugin provides the
  default `_csvparsefailure` tag.
- Both pipelines then passed:

```text
Configuration OK
```

- Explicit `*.part` exclusions were added to both CSV and JSON file inputs.
- The pipeline config was checked with:

```bash
docker compose run --rm --no-deps logstash --config.test_and_exit
```

## Elasticsearch template

- The template JSON passed parsing and formatting checks.
- Applying it initially found an existing priority conflict with a `logs`
  template. Priority was raised to 200.
- Elasticsearch then reported that `logs-saas-*` names were existing data
  streams, so `data_stream: {}` was added.
- The template was successfully applied and verified with the requested field
  mappings, one shard, and zero replicas.

## Atlas connection

- A malformed URI first produced an empty DNS label error.
- A stale exported shell `MONGO_URI` then overrode the corrected `.env` value.
- Running `unset MONGO_URI` and recreating the webapp loaded the correct `.env`
  value.
- Atlas connectivity and MongoDB index creation then passed.

## End-to-end upload smoke test

The test used 500 Faker-generated CSV records:

```bash
python scripts/generate_logs.py --count 500 --format csv --output sample.csv
BEFORE=$(curl -s "localhost:9200/logs-saas-*/_count" | python3 -c "import sys,json;print(json.load(sys.stdin).get('count',0))")
curl -s -F "file=@sample.csv" localhost:8000/upload
AFTER=$(curl -s "localhost:9200/logs-saas-*/_count" | python3 -c "import sys,json;print(json.load(sys.stdin).get('count',0))")
```

The first run exposed a real permission issue: the upload returned HTTP 500
because the named volume was initialized by Logstash as root. The non-root
webapp could not create its `.part` file. After adding a startup ownership
initializer, the upload returned HTTP 202, but the completed file remained mode
0600 and Logstash could not read it. The source was then corrected to chmod the
completed temporary file to 0644 before the atomic rename.

The final runtime rebuild/recreate after the 0644 fix is still pending because
that command was skipped during the current session. The required next check
is:

```bash
docker compose build webapp
docker compose up -d --force-recreate webapp
# Generate and upload 500 records, then verify the logs-saas count increases.
```
