"""Application routes."""

from flask import Blueprint, jsonify

from app.clients import check_all

main = Blueprint("main", __name__)


@main.get("/")
def index():
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LogLens</title>
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; background: #f4f7fb; color: #172033; }
    nav { display: flex; align-items: center; gap: 1.25rem; padding: 1rem 2rem; background: #172033; }
    nav strong { color: white; margin-right: auto; font-size: 1.1rem; }
    nav a { color: #dfe8f5; text-decoration: none; }
    nav a:hover { color: white; }
    main { max-width: 760px; margin: 4rem auto; padding: 0 1.5rem; }
  </style>
</head>
<body>
  <nav aria-label="Main navigation">
    <strong>LogLens</strong>
    <a href="/">Home</a>
    <a href="/upload">Upload</a>
    <a href="/health">Health</a>
    <a href="/apidocs/">Swagger</a>
    <a href="http://localhost:5601" target="_blank" rel="noopener">Kibana</a>
  </nav>
  <main>
    <h1>LogLens</h1>
    <p>Upload and monitor CSV, JSON, and TXT logs through the ELK stack.</p>
  </main>
</body>
</html>"""


@main.get("/health")
def health():
    """
    Report application dependency health.
    ---
    tags:
      - health
    produces:
      - application/json
    responses:
      200:
        description: Dependency statuses and aggregate health.
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [healthy, degraded, down]
            dependencies:
              type: object
    """
    dependencies = check_all()
    statuses = [result["status"] for result in dependencies.values()]
    if all(status == "up" for status in statuses):
        status = "healthy"
    elif all(status == "down" for status in statuses):
        status = "down"
    else:
        status = "degraded"
    return jsonify(status=status, dependencies=dependencies)
