"""Lazy clients and dependency checks for LogLens backends."""

import logging
import os
import time
from typing import Callable

from elasticsearch import Elasticsearch
from pymongo import MongoClient
from redis import Redis

logger = logging.getLogger(__name__)

_es_client: Elasticsearch | None = None
_mongo_client: MongoClient | None = None
_mongo_db = None
_redis_client: Redis | None = None


def get_es() -> Elasticsearch:
    """Return the lazily-created Elasticsearch client."""
    global _es_client
    if _es_client is None:
        _es_client = Elasticsearch(
            os.getenv("ES_HOST", "http://elasticsearch:9200"),
            request_timeout=5,
        )
    return _es_client


def get_mongo_db():
    """Return the lazily-created MongoDB database handle."""
    global _mongo_client, _mongo_db
    if _mongo_db is None:
        _mongo_client = MongoClient(
            os.getenv("MONGO_URI", "mongodb://mongodb:27017"),
            serverSelectionTimeoutMS=5000,
        )
        _mongo_db = _mongo_client[os.getenv("MONGO_DB", "loglens")]
    return _mongo_db


def get_redis() -> Redis:
    """Return the lazily-created Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client


def _check(operation: Callable[[], object]) -> dict[str, object]:
    started = time.perf_counter()
    try:
        operation()
        return {
            "status": "up",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": None,
        }
    except Exception as exc:  # A health endpoint must report dependency failures.
        return {
            "status": "down",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": str(exc),
        }


def check_es() -> dict[str, object]:
    return _check(lambda: get_es().cluster.health())


def check_mongo() -> dict[str, object]:
    return _check(lambda: get_mongo_db().client.admin.command("ping"))


def check_redis() -> dict[str, object]:
    return _check(lambda: get_redis().ping())


def check_all() -> dict[str, dict[str, object]]:
    return {
        "elasticsearch": check_es(),
        "mongodb": check_mongo(),
        "redis": check_redis(),
    }


def _create_mongo_indexes() -> None:
    database = get_mongo_db()
    database.files.create_index([("uploaded_at", 1), ("status", 1)])
    database.searches.create_index([("executed_at", 1)])
    logger.info("MongoDB indexes ready: files(uploaded_at, status), searches(executed_at)")


def startup_checks(retries: int = 3) -> dict[str, dict[str, object]]:
    """Check dependencies and create MongoDB indexes without blocking startup."""
    checks = {
        "elasticsearch": check_es,
        "mongodb": check_mongo,
        "redis": check_redis,
    }
    results: dict[str, dict[str, object]] = {}

    for name, check in checks.items():
        result = None
        for attempt in range(1, retries + 1):
            result = check()
            if result["status"] == "up":
                logger.info("Startup dependency check %s: up (attempt %d/%d, %.2f ms)", name, attempt, retries, result["latency_ms"])
                break
            logger.warning("Startup dependency check %s: down (attempt %d/%d): %s", name, attempt, retries, result["error"])
            if attempt < retries:
                time.sleep(1)
        results[name] = result
        if result["status"] == "down":
            logger.error("Startup dependency unavailable: %s; application will continue", name)

    if results["mongodb"]["status"] == "up":
        try:
            _create_mongo_indexes()
        except Exception as exc:
            logger.error("MongoDB index creation failed; application will continue: %s", exc)
    else:
        logger.warning("Skipping MongoDB index creation because MongoDB is unavailable")

    return results
