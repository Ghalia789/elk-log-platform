#!/usr/bin/env sh
set -eu

ELASTICSEARCH_URL=${ELASTICSEARCH_URL:-http://localhost:9200}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TEMPLATE_PATH="$SCRIPT_DIR/../elasticsearch/index-template.json"

printf 'Waiting for Elasticsearch at %s...\n' "$ELASTICSEARCH_URL"
curl --fail --silent --show-error \
  --retry 60 \
  --retry-delay 2 \
  --retry-connrefused \
  --retry-all-errors \
  "$ELASTICSEARCH_URL/_cluster/health?wait_for_status=yellow&timeout=5s" >/dev/null

curl --fail --silent --show-error \
  -X PUT \
  -H 'Content-Type: application/json' \
  --data-binary "@$TEMPLATE_PATH" \
  "$ELASTICSEARCH_URL/_index_template/logs-saas"
printf '\nApplied logs-saas index template.\n'
