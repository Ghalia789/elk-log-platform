"""Best-effort Redis caching for search and statistics responses."""

import hashlib
import json

from app.clients import get_redis


def _search_key(params):
	normalized = json.dumps(params, sort_keys=True, separators=(",", ":"))
	return "cache:search:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _get_json(key):
	try:
		value = get_redis().get(key)
		return json.loads(value) if value else None
	except Exception:
		return None


def _set_json(key, value, ttl):
	try:
		get_redis().set(key, json.dumps(value, separators=(",", ":")), ex=ttl)
	except Exception:
		pass


def get_search(params):
	return _get_json(_search_key(params))


def set_search(params, value):
	_set_json(_search_key(params), value, 60)


def get_stats():
	return _get_json("cache:stats")


def set_stats(value):
	_set_json("cache:stats", value, 15)


def invalidate_searches():
	try:
		redis = get_redis()
		for key in redis.scan_iter(match="cache:search:*"):
			redis.delete(key)
	except Exception:
		pass