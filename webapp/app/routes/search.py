"""Log search and search history routes."""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.clients import get_es, get_mongo_db
from app.services.cache import get_search, set_search
from app.services.search_query import build_query, pagination_offset, parse_search_params

logger = logging.getLogger(__name__)
search = Blueprint("search", __name__)


def _items(response):
	return [
		{
			"id": hit["_id"],
			"timestamp": hit.get("_source", {}).get("@timestamp"),
			"level": hit.get("_source", {}).get("level"),
			"service": hit.get("_source", {}).get("service"),
			"endpoint": hit.get("_source", {}).get("endpoint"),
			"status_code": hit.get("_source", {}).get("status_code"),
			"response_time_ms": hit.get("_source", {}).get("response_time_ms"),
			"message": hit.get("_source", {}).get("message"),
		}
		for hit in response["hits"]["hits"]
	]


def run_search(params):
	result = get_search(params)
	cache_status = "HIT" if result is not None else "MISS"
	if result is None:
		response = get_es().search(
			index="logs-saas-*",
			query=build_query(params),
			from_=pagination_offset(params),
			size=params["per_page"],
			sort=[{"@timestamp" if params["sort"] == "timestamp" else params["sort"]: {"order": params["order"]}}],
			track_total_hits=True,
		)
		total = response["hits"]["total"]
		result = {
			"total": total["value"] if isinstance(total, dict) else total,
			"page": params["page"],
			"per_page": params["per_page"],
			"took_ms": response.get("took", 0),
			"items": _items(response),
		}
		set_search(params, result)

	try:
		get_mongo_db().searches.insert_one({
			"query": params["q"],
			"filters": {key: value for key, value in params.items() if key != "q"},
			"result_count": result["total"],
			"executed_at": datetime.now(timezone.utc),
		})
	except Exception as error:
		logger.warning("Could not save search history: %s", error)
	return result, cache_status


@search.get("/search")
def search_logs():
	try:
		params = parse_search_params(request.args)
	except ValueError as error:
		return jsonify(error=str(error), code="invalid_parameters"), 400
	try:
		result, cache_status = run_search(params)
		return jsonify(result), 200, {"X-Cache": cache_status}
	except Exception:
		logger.exception("Log search failed")
		return jsonify(error="Search service unavailable.", code="search_unavailable"), 503


@search.get("/search/history")
def search_history():
	try:
		records = list(get_mongo_db().searches.find({}, {"_id": 0}).sort("executed_at", -1).limit(50))
		for record in records:
			if isinstance(record.get("executed_at"), datetime):
				record["executed_at"] = record["executed_at"].replace(tzinfo=timezone.utc).isoformat()
		return jsonify(items=records)
	except Exception:
		logger.exception("Could not load search history")
		return jsonify(error="Search history unavailable.", code="history_unavailable"), 503