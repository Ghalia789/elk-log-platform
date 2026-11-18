# LogLens

## Overview

LogLens is a SaaS log monitoring platform for uploading CSV, JSON, and TXT log
files, parsing them with Logstash, indexing them in Elasticsearch, and
searching or visualizing them through Flask and Kibana.

## Architecture

The Flask application stores uploaded files in the shared `uploads` volume as
`<upload_id>__<original_name>`. Logstash reads that volume, parses the files,
and sends events to Elasticsearch in `logs-saas-*` indices. MongoDB Atlas stores
file metadata and search history by default, while Redis stores cache entries
and sessions. A local MongoDB 7 container remains available through the
`local-mongo` profile for machines with AVX support.

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

The default setup uses MongoDB Atlas through `MONGO_URI`. To use the optional
local MongoDB container instead, set `MONGO_URI=mongodb://mongodb:27017` and
start the profile:

```bash
docker compose --profile local-mongo up -d
```

Open Kibana at http://localhost:5601. Stop the stack with:

```bash
docker compose down
```

Named volumes retain Elasticsearch data, Logstash sincedb state, and uploaded
files between restarts.

## Generate sample logs

Faker is included in `webapp/requirements.txt`. Install the project
requirements, then generate CSV or newline-delimited JSON logs:

```bash
pip install -r webapp/requirements.txt
python3 scripts/generate_logs.py --count 1000 --format json --output uploads/sample.json
python3 scripts/generate_logs.py --count 1000 --format csv --output uploads/sample.csv
```

The default count is 10,000 logs. Use `--output -` to write the selected
format to standard output.

## Ingest logs with Logstash

Generate a CSV file, start the stack, and copy the file into the shared named
volume through the read-write webapp mount. The filename prefix is the upload
ID used by the Logstash `dissect` filter:

```bash
python3 scripts/generate_logs.py --count 1000 --format csv --output /tmp/loglens.csv
docker compose up -d
UPLOAD_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
docker compose cp /tmp/loglens.csv "webapp:/uploads/${UPLOAD_ID}__sample.csv"
```

Follow Logstash processing and inspect completed files:

```bash
docker compose logs -f logstash
docker compose exec logstash sh -c 'cat /usr/share/logstash/data/completed_csv.log'
```

Check the generated daily indices and documents in Elasticsearch:

```bash
curl "http://localhost:9200/_cat/indices/logs-saas-*?v"
curl "http://localhost:9200/logs-saas-*/_search?pretty&size=3"
```

In Kibana, open **Stack Management > Data Views**, create a data view named
`logs-saas-*`, and select `@timestamp` as the time field. Then use **Discover**
to inspect the indexed log documents.

## Apply the Elasticsearch template

With Elasticsearch running, apply the `logs-saas-*` index template:

```bash
./scripts/apply_template.sh
```

The script waits for Elasticsearch, then sends a `PUT` request to
`_index_template/logs-saas`. Check the template and its mappings with:

```bash
curl "http://localhost:9200/_index_template/logs-saas?pretty"
curl "http://localhost:9200/logs-saas-*/_mapping?pretty"
```

## Environment variables

Configuration is supplied through `.env`; do not commit that file.

| Name | Meaning | Default |
|---|---|---|
| `ELK_VERSION` | Shared Elasticsearch, Kibana, and Logstash image tag | `8.15.3` |
| `ES_HOST` | Elasticsearch URL used by Flask | `http://elasticsearch:9200` |
| `ES_JAVA_OPTS` | Elasticsearch heap size | `-Xms512m -Xmx512m` |
| `MONGO_URI` | MongoDB Atlas URI by default, or local URI with the profile | `mongodb+srv://<username>:<password>@<cluster-host>/loglens` |
| `MONGO_DB` | MongoDB application database name | `loglens` |
| `MONGO_ROOT_USER` | Local MongoDB root username; profile only | `loglens_admin` |
| `MONGO_ROOT_PASSWORD` | Local MongoDB root password; profile only | `replace-with-a-local-password` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `FLASK_ENV` | Flask runtime environment | `development` |
| `UPLOAD_DIR` | Upload directory used by Flask | `/uploads` |
| `MAX_UPLOAD_MB` | Maximum upload size in megabytes | `100` |

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
- MongoDB Atlas is the default because MongoDB 7 requires AVX, which may not be
  exposed by older virtual machines. If using the local profile, verify AVX is
  available and inspect `docker compose logs mongodb`.
- If Atlas cannot be reached, check the Atlas Network Access allowlist,
  database credentials, and the `MONGO_URI` value in the ignored `.env` file.
- If Logstash does not process uploads, confirm the file is in the shared
  `uploads` volume and that a configuration exists in `logstash/pipeline/`.
- Recreate containers without deleting data with `docker compose up -d --force-recreate`.
- To remove all named volumes and their data, use `docker compose down -v`.
