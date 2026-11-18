"""Application routes."""

from flask import Blueprint, jsonify

from app.clients import check_all

main = Blueprint("main", __name__)


@main.get("/")
def index():
    return "<h1>Hello World</h1>"


@main.get("/health")
def health():
    dependencies = check_all()
    statuses = [result["status"] for result in dependencies.values()]
    if all(status == "up" for status in statuses):
        status = "healthy"
    elif all(status == "down" for status in statuses):
        status = "down"
    else:
        status = "degraded"
    return jsonify(status=status, dependencies=dependencies)
