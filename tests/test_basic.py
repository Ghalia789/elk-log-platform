"""Small service-free tests for validation and Elasticsearch query helpers."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "webapp"))

from app.services.search_query import build_query, pagination_offset
from app.services.validation import EXPECTED_COLUMNS, ValidationError, validate_csv, validate_json, validate_upload


def test_valid_csv_passes_validation():
	header = ",".join(EXPECTED_COLUMNS)
	row = "2026-11-25T10:00:00Z,INFO,api,/health,GET,200,12.5,192.0.2.1,u1,t1,ok"
	validate_csv(f"{header}\n{row}\n".encode())


def test_csv_with_wrong_column_count_fails():
	header = ",".join(EXPECTED_COLUMNS)
	content = f"{header}\nonly,two\n".encode()
	with pytest.raises(ValidationError):
		validate_csv(content)


def test_invalid_json_line_fails():
	with pytest.raises(ValidationError):
		validate_json(b'{"message": broken}\n')


def test_wrong_extension_fails():
	with pytest.raises(ValidationError):
		validate_upload("logs.exe", b"", 1024)


def test_build_query_text_only():
	assert build_query({"q": "error timeout"}) == {
		"bool": {
			"must": [{"simple_query_string": {"query": "error timeout", "fields": ["message"]}}],
			"filter": [],
		}
	}


def test_build_query_level_filter():
	assert build_query({"level": "ERROR"}) == {
		"bool": {"must": [], "filter": [{"term": {"level": "ERROR"}}]}
	}


def test_build_query_date_range():
	assert build_query({"from": "2026-11-25T00:00:00+00:00", "to": "2026-11-25T23:59:59+00:00"}) == {
		"bool": {
			"must": [],
			"filter": [{"range": {"@timestamp": {
				"gte": "2026-11-25T00:00:00+00:00",
				"lte": "2026-11-25T23:59:59+00:00",
			}}}],
		}
	}


def test_pagination_offset():
	assert pagination_offset({"page": 3, "per_page": 50}) == 100