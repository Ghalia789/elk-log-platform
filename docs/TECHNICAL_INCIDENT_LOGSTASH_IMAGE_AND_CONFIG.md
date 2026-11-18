# Technical incident: Logstash image pull and pipeline validation

- **Date:** 2026-11-11
- **Component:** Docker Compose / Logstash 8.15.3
- **Status:** Resolved
- **Severity:** Development environment startup issue

## Symptoms

The Logstash validation command appeared to keep downloading or extracting
large image layers:

```text
docker compose run --rm --no-deps logstash --config.test_and_exit
```

A later `docker compose up -d` also spent a long time pulling Elasticsearch,
Kibana, and MongoDB images. During the first successful Logstash validation,
Logstash reported:

```text
[ERROR][logstash.filters.csv] Unknown setting 'tag_on_failure' for csv
[FATAL][logstash.runner] The given configuration is invalid
```

## Root cause

There were two independent issues:

1. **The image was not fully available locally.** `docker compose run` must
   pull the service image when it is missing. The first Logstash image pull was
   interrupted or stalled during layer extraction. Docker therefore continued
   pulling or extracting layers the next time the command was run. This was
   image download work, not a reinstall of Python packages or Logstash plugins.
2. **The CSV pipeline contained an unsupported option.** Logstash 8.15.3's
   CSV filter does not accept `tag_on_failure`. The CSV filter already applies
   its default `_csvparsefailure` tag when parsing fails.

The host already had some older ELK images such as 8.15.0, while `.env` pins
this project to 8.15.3. Docker correctly pulled new 8.15.3 images because
Docker tags are part of the image identity; an existing 8.15.0 image cannot
satisfy an 8.15.3 request.

## Resolution

- Removed `tag_on_failure` from `logstash/pipeline/csv.conf`.
- Kept the default CSV parse-failure tag `_csvparsefailure`.
- Confirmed both pipelines with:

```bash
docker compose run --rm --no-deps logstash --config.test_and_exit
```

The final result was:

```text
Pipeline `csv` ... configured
Pipeline `json` ... configured
Configuration OK
```

The uploaded fixture also remained available in the named volume:

```text
/uploads/test01__sample.csv
```

## Why it looked like it was reinstalling repeatedly

Docker Compose does not reinstall the project on every command. The observed
repetition came from these behaviors:

- `docker compose run` creates a temporary container and may pull its image if
  that image is not locally available.
- `docker compose up` checks every service in the Compose file and pulls any
  missing image, not just Logstash.
- Large Elasticsearch, Kibana, MongoDB, and Logstash layers can take a long
  time to download and extract.
- A different pinned tag, such as 8.15.3 instead of an existing 8.15.0,
  requires a separate image.
- `--rm` removes the temporary validation container after it exits, but it does
  not remove successfully downloaded images or named volumes.

To distinguish image work from container work, use:

```bash
docker image ls
docker ps -a
docker compose ps -a
docker system df
```

## Recommended diagnostic sequence

```bash
# Check the requested image tag and local availability.
docker image inspect docker.elastic.co/logstash/logstash:8.15.3

# Validate Compose without starting containers.
docker compose config --quiet

# Validate Logstash configuration without dependencies.
docker compose run --rm --no-deps logstash --config.test_and_exit

# Start the stack after images are available.
docker compose up -d

# Inspect runtime state and logs.
docker compose ps -a
docker compose logs logstash --tail 50
```

If an image pull is genuinely stuck, check Docker daemon/network conditions
first. Avoid deleting volumes unless data loss is acceptable; the named
`uploads` volume contains uploaded fixtures and the Logstash data volume
contains sincedb state.

## MongoDB workaround

The VM does not expose AVX, which prevents MongoDB 7 from starting. LogLens
therefore uses MongoDB Atlas through `MONGO_URI` by default. The local MongoDB
7 service remains available only through the `local-mongo` profile for a host
or VM with AVX support:

```bash
docker compose --profile local-mongo up -d
```

For Atlas mode, configure `MONGO_URI` and `MONGO_DB` in the ignored `.env`
file. The webapp does not depend on the local MongoDB service in the default
profile.
