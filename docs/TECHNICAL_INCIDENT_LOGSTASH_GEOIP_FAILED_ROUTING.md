# Technical incident: Logstash GeoIP startup and failed-event routing

- **Date:** 2026-11-25
- **Component:** Logstash 8.15.3, CSV and JSON pipelines
- **Status:** Partially resolved
- **Severity:** Development ingestion and verification issue

## Symptoms

The CSV and JSON upload checks did not produce the expected split of five valid
records in `logs-saas-*` and one invalid-timestamp record in `logs-failed-*`.
Initially, the Logstash pipeline API listed no active CSV or JSON pipelines and
Elasticsearch had no matching documents. After the pipeline startup issue was
fixed, the check reported:

```text
sample.csv ... saas=5 failed=0
sample.ndjson ... saas=5 failed=0
```

The invalid-timestamp records were not counted in either expected failed count.

## Root cause and contributing issues

1. **GeoIP prevented pipeline startup.** With ECS compatibility enabled,
   Logstash 8.15.3 requires an explicit `target` when GeoIP reads the top-level
   `client_ip` field. Both pipelines lacked it and failed during registration.
2. **The integration fixtures initially bypassed upload validation.** Copying
   files directly into the shared volume did not exercise the Flask upload
   endpoint. The malformed CSV row was also rejected by Flask because its field
   count was wrong. The fixtures were changed to structurally valid rows with
   `timestamp` set to `not-a-date`, and the checker was switched to HTTP uploads.
3. **Failed-event routing remains unverified.** After adding the GeoIP target,
   the API listed both `csv` and `json`, and five valid rows per upload appeared
   in `logs-saas-*`. The expected sixth rows did not appear in the failed counts.
   No event-level evidence from this run confirms whether the date filter tagged
   those rows or whether the output condition routed them as intended.

## Resolution so far

- Added `target => "geoip"` to both GeoIP filters, preserving the public-IP
  condition and `tag_on_failure => []`. The target matches the index template's
  `geoip.location` field structure.
- Restarted only Logstash once. The pipeline API subsequently listed `csv` and
  `json` as active.
- Updated the checker to count failed-index documents using a bool query over
  `upload_id`, `upload_id.keyword`, and `match_phrase`.

The GeoIP change removes the fatal startup error. Logstash emits a non-fatal ECS
warning because `geoip` is outside its preferred ECS target names; it is retained
to match the existing index template.

## Remaining investigation

The next diagnostic should establish what happened to the invalid-timestamp
record for a newly uploaded fixture: confirm the parsed event has the upload ID
and `_dateparsefailure` tag, then verify the failed-output condition and the
resulting `logs-failed-*` document. Do not treat the five SaaS records alone as a
passing pipeline check; the expected result remains `saas=5 failed=1` per file.

## Verification history

- Before the GeoIP change: pipeline API showed an empty `pipelines` object;
  logs reported that GeoIP required a target.
- After the GeoIP change: the API listed both `csv` and `json`.
- The upload checker then reported `saas=5 failed=0` for each fixture, including
  after broadening the failed-index upload ID query.
