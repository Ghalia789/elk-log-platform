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
	"""
	Search indexed log events through the versioned API.
	---
	tags:
	  - logs
	parameters:
	  - {name: q, in: query, type: string, required: false, description: Text query matched against message.}
	  - {name: level, in: query, type: string, required: false}
	  - {name: service, in: query, type: string, required: false}
	  - {name: from, in: query, type: string, format: date-time, required: false}
	  - {name: to, in: query, type: string, format: date-time, required: false}
	  - {name: page, in: query, type: integer, minimum: 1, default: 1, required: false}
	  - {name: per_page, in: query, type: integer, minimum: 1, maximum: 200, default: 50, required: false}
	  - {name: sort, in: query, type: string, enum: [timestamp, level, service], default: timestamp, required: false}
	  - {name: order, in: query, type: string, enum: [asc, desc], default: desc, required: false}
	produces:
	  - application/json
	responses:
	  200:
	    description: Search results and pagination metadata.
	    schema:
	      type: object
	      properties:
	        total: {type: integer}
	        page: {type: integer}
	        per_page: {type: integer}
	        took_ms: {type: integer}
	        items: {type: array, items: {type: object}}
	  400:
	    description: Invalid search parameters.
	  503:
	    description: Search service unavailable.
	"""
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
	"""
	Retrieve one indexed log event by Elasticsearch document ID.
	---
	tags:
	  - logs
	parameters:
	  - name: log_id
	    in: path
	    type: string
	    required: true
	produces:
	  - application/json
	responses:
	  200:
	    description: The requested log event.
	    schema:
	      type: object
	      properties:
	        id: {type: string}
	        timestamp: {type: string, format: date-time}
	        level: {type: string}
	        service: {type: string}
	        endpoint: {type: string}
	        status_code: {type: integer}
	        response_time_ms: {type: number}
	        message: {type: string}
	  404:
	    description: Log event not found.
	  503:
	    description: Log service unavailable.
	"""
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
	"""
	List uploaded file metadata.
	---
	tags:
	  - uploads
	parameters:
	  - {name: status, in: query, type: string, required: false, enum: [pending, indexed, failed]}
	  - {name: from, in: query, type: string, format: date-time, required: false, description: Include uploads at or after this time.}
	  - {name: to, in: query, type: string, format: date-time, required: false, description: Include uploads at or before this time.}
	  - {name: page, in: query, type: integer, minimum: 1, default: 1, required: false}
	  - {name: per_page, in: query, type: integer, minimum: 1, maximum: 200, default: 50, required: false}
	produces:
	  - application/json
	responses:
	  200:
	    description: Uploaded files and pagination metadata.
	    schema:
	      type: object
	      properties:
	        items: {type: array, items: {type: object}}
	        total: {type: integer}
	        page: {type: integer}
	        per_page: {type: integer}
	  400:
	    description: Invalid query parameters.
	  503:
	    description: File service unavailable.
	"""
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
	"""
	Return aggregate log and upload statistics.
	---
	tags:
	  - statistics
	produces:
	  - application/json
	responses:
	  200:
	    description: Aggregate counts and log breakdowns.
	    schema:
	      type: object
	      properties:
	        total_logs: {type: integer}
	        logs_today: {type: integer}
	        error_logs: {type: integer}
	        files_uploaded: {type: integer}
	        logs_by_level: {type: object}
	        logs_per_hour: {type: array, items: {type: object}}
	  503:
	    description: Statistics service unavailable.
	"""
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