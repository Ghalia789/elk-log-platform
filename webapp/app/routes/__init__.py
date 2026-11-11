"""Application routes."""

from flask import Blueprint, jsonify

main = Blueprint("main", __name__)


@main.get("/")
def index():
    return "<h1>Hello World</h1>"


@main.get("/health")
def health():
    return jsonify(status="ok")
