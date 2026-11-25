#!/usr/bin/env bash
set -euo pipefail

es_url="${ES_URL:-http://localhost:9200}"

count_documents() {
	local index="$1"
	local upload_id="$2"
	local field="$3"
	curl -s -H 'Content-Type: application/json' \
		--data-binary "{\"query\":{\"term\":{\"${field}\":\"${upload_id}\"}}}" \
		"${es_url}/${index}/_count" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("count", 0))'
}

count_failed_documents() {
	local index="$1"
	local upload_id="$2"
	curl -s -X POST -H 'Content-Type: application/json' \
		--data-binary "{\"query\":{\"bool\":{\"should\":[{\"term\":{\"upload_id\":\"${upload_id}\"}},{\"term\":{\"upload_id.keyword\":\"${upload_id}\"}},{\"match_phrase\":{\"upload_id\":\"${upload_id}\"}}],\"minimum_should_match\":1}}}" \
		"${es_url}/${index}/_count" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("count", 0))'
}

check_upload() {
	local fixture="$1"
	local multipart_file="$2"
	local response upload_id error saas failed deadline
	response="$(curl -s -F "file=@tests/fixtures/${fixture}${multipart_file}" localhost:8000/upload)"
	upload_id="$(printf '%s' "$response" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("upload_id", ""))' 2>/dev/null || true)"
	error="$(printf '%s' "$response" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("error", ""))' 2>/dev/null || true)"
	if [[ -n "$error" || -z "$upload_id" ]]; then
		printf '%s upload_id= saas=0 failed=0\n' "$fixture"
		printf '%s\n' "$response"
		printf 'FAIL\n'
		return 1
	fi

	saas=0
	failed=0
	deadline=$((SECONDS + 45))
	while :; do
		saas="$(count_documents 'logs-saas-*' "$upload_id" 'upload_id.keyword')"
		if (( saas == 0 )); then
			saas="$(count_documents 'logs-saas-*' "$upload_id" 'upload_id')"
		fi
		failed="$(count_failed_documents 'logs-failed-*' "$upload_id")"
		if (( saas >= 5 && failed >= 1 )) || (( SECONDS >= deadline )); then
			break
		fi
		sleep 3
	done

	printf '%s upload_id=%s saas=%s failed=%s\n' "$fixture" "$upload_id" "$saas" "$failed"
	if (( saas == 5 && failed == 1 )); then
		printf 'PASS\n'
		return 0
	fi
	printf 'FAIL\n'
	return 1
}

result=0
check_upload sample.csv "" || result=1
check_upload sample.ndjson ";filename=sample.json" || result=1
exit "$result"