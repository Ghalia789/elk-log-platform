"""Versioned REST API for logs, files, and statistics."""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.clients import get_es, get_mongo_db
from app.models.files import list_files
from app.routes.search import run_search, _items
from app.services.cache import get_stats, set_stats
from app.services.search_query import parse_search_params

logger = logging.getLogger(__name__)
api = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _error(message, code, status):
	return jsonify(error=message, code=code), status


def _file_json(document):
	return {
		"upload_id": document.get("upload_id"),
		"filename": document.get("filename"),
		"size_bytes": document.get("size_bytes"),
		"format": document.get("format"),
		"status": document.get("status"),
		"uploaded_at": document.get("uploaded_at").isoformat() if document.get("uploaded_at") else None,
		"log_count": document.get("log_count", 0),
	}


@api.get("/logs")
def logs():
	try:
		params = parse_search_params(request.args)
		result, cache_status = run_search(params)
		return jsonify(result), 200, {"X-Cache": cache_status}
	except ValueError as error:
		return _error(str(error), "invalid_parameters", 400)
	except Exception:
		logger.exception("API log search failed")
		return _error("Search service unavailable.", "search_unavailable", 503)


@api.get("/logs/<log_id>")
def log_by_id(log_id):
	try:
		response = get_es().search(
			index="logs-saas-*",
			query={"ids": {"values": [log_id]}},
			size=1,
	)
		items = _items(response)
		if not items:
			return _error("Log not found.", "not_found", 404)
		return jsonify(items[0])
	except Exception:
		logger.exception("Could not retrieve log %s", log_id)
		return _error("Log service unavailable.", "log_unavailable", 503)


@api.get("/files")
def files():
	try:
		params = parse_search_params(request.args)
		status = request.args.get("status") or None
		date_from = datetime.fromisoformat(params["from"]) if params["from"] else None
		date_to = datetime.fromisoformat(params["to"]) if params["to"] else None
		result = list_files(params["page"], params["per_page"], status, date_from, date_to)
		return jsonify(
			items=[_file_json(document) for document in result["items"]],
			total=result["total"],
			page=result["page"],
			per_page=result["per_page"],
		)
	except ValueError as error:
		return _error(str(error), "invalid_parameters", 400)
	except Exception:
		logger.exception("Could not retrieve uploaded files")
		return _error("File service unavailable.", "files_unavailable", 503)


@api.get("/stats")
def stats():
	result = get_stats()
	if result is not None:
		return jsonify(result)
	try:
		response = get_es().search(
			index="logs-saas-*",
			size=0,
			track_total_hits=True,
			aggs={
				"logs_today": {"filter": {"range": {"@timestamp": {"gte": "now/d"}}}},
				"error_logs": {"filter": {"terms": {"level": ["ERROR", "CRITICAL"]}}},
				"logs_by_level": {"terms": {"field": "level", "size": 50}},
				"logs_per_hour": {
					"date_histogram": {
						"field": "@timestamp",
						"fixed_interval": "1h",
						"min_doc_count": 0,
						"extended_bounds": {"min": "now-24h", "max": "now"},
					}
				},
			},
		)
		aggs = response["aggregations"]
		result = {
			"total_logs": response["hits"]["total"]["value"],
			"logs_today": aggs["logs_today"]["doc_count"],
			"error_logs": aggs["error_logs"]["doc_count"],
			"files_uploaded": get_mongo_db().files.count_documents({}),
			"logs_by_level": {bucket["key"]: bucket["doc_count"] for bucket in aggs["logs_by_level"]["buckets"]},
			"logs_per_hour": [
				{"hour": bucket["key_as_string"], "count": bucket["doc_count"]}
				for bucket in aggs["logs_per_hour"]["buckets"]
			],
		}
		set_stats(result)
		return jsonify(result)
	except Exception:
		logger.exception("Could not retrieve statistics")
		return _error("Statistics service unavailable.", "stats_unavailable", 503)