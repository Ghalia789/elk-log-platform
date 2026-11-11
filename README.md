# LogLens

## Overview

LogLens is a SaaS log monitoring platform for uploading CSV, JSON, and TXT log
files, parsing them with Logstash, indexing them in Elasticsearch, and
searching or visualizing them through Flask and Kibana.

## Architecture

The Flask application stores uploaded files in the shared `uploads` volume as
`<upload_id>__<original_name>`. Logstash reads that volume, parses the files,
and sends events to Elasticsearch in `logs-saas-*` indices. MongoDB stores file
metadata and search history, while Redis stores cache entries and sessions.

The ELK services communicate over the `elk-net` Docker bridge network.

## Requirements

- Docker Engine with Docker Compose v2
- At least 4 GB of available memory for the local stack
- A Unix-like shell or equivalent Docker environment

## Quick start

```bash
cp .env.example .env
docker compose up -d
docker compose ps
```

Open Kibana at http://localhost:5601. Stop the stack with:

```bash
docker compose down
```

Named volumes retain Elasticsearch data, Logstash sincedb state, and uploaded
files between restarts.

## Environment variables

Configuration is supplied through `.env`; do not commit that file.

| Variable | Example | Purpose |
|---|---|---|
| `ELK_VERSION` | `8.15.3` | Shared Elasticsearch, Kibana, and Logstash image tag |
| `ES_JAVA_OPTS` | `-Xms512m -Xmx512m` | Elasticsearch heap size |
| `ES_HOST` | `http://elasticsearch:9200` | Elasticsearch URL used by application services |
| `MONGO_URI` | `mongodb://mongo:27017/logs` | MongoDB connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `UPLOAD_DIR` | `/uploads` | Upload directory used by Flask |
| `MAX_UPLOAD_MB` | `50` | Maximum upload size |

Copy `.env.example` to `.env` and adjust values for the local environment.

## Services and ports

| Service | Port | Purpose |
|---|---:|---|
| Elasticsearch | 9200 | Search and log storage |
| Kibana | 5601 | Dashboards and visualization |
| Logstash | 9600 | Logstash monitoring API |
| Flask webapp | 8000 | Upload and search API/UI |
| MongoDB | 27017 | Metadata and search history |
| Redis | 6379 | Cache and sessions |

Check the ELK services with:

```bash
curl http://localhost:9200/_cluster/health
curl http://localhost:5601/api/status
curl http://localhost:9600/?pretty
```

## Troubleshooting

- View service logs with `docker compose logs -f <service>`.
- Check container state with `docker compose ps`.
- If Elasticsearch is unhealthy, confirm Docker has enough memory and inspect
  `docker compose logs elasticsearch`.
- If Logstash does not process uploads, confirm the file is in the shared
  `uploads` volume and that a configuration exists in `logstash/pipeline/`.
- Recreate containers without deleting data with `docker compose up -d --force-recreate`.
- To remove all named volumes and their data, use `docker compose down -v`.
