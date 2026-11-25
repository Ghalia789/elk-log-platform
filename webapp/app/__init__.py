"""LogLens Flask application factory."""

import logging
import os

from flask import Flask, jsonify
from flasgger import Swagger
from werkzeug.exceptions import RequestEntityTooLarge

from app.clients import startup_checks
from app.routes import main
from app.routes.api import api
from app.routes.search import search
from app.routes.upload import upload


def configure_logging() -> None:
	level_name = os.getenv("LOG_LEVEL", "INFO").upper()
	level = getattr(logging, level_name, logging.INFO)
	logging.basicConfig(
		level=level,
		format="%(asctime)s %(levelname)s %(name)s: %(message)s",
	)
	logging.getLogger().setLevel(level)


def create_app() -> Flask:
	"""Create and configure the Flask application."""
	configure_logging()
	app = Flask(__name__)
	max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "100"))
	app.config["MAX_CONTENT_LENGTH"] = max_upload_mb * 1024 * 1024
	Swagger(
		app,
		config={
			"oauth": {},
			"headers": [],
			"static_url_path": "/flasgger_static",
			"specs": [{
				"endpoint": "apispec_1",
				"route": "/apispec_1.json",
				"rule_filter": lambda rule: True,
				"model_filter": lambda tag: True,
			}],
		},
		template={
			"swagger": "2.0",
			"info": {
				"title": "LogLens API",
				"description": "Log upload, preview, and dependency health API for the LogLens ELK platform.",
				"version": "1.0.0",
			},
		},
	)
	app.register_blueprint(main)
	app.register_blueprint(upload)
	app.register_blueprint(search)
	app.register_blueprint(api)

	@app.errorhandler(RequestEntityTooLarge)
	def handle_request_entity_too_large(error):
		return jsonify(error="file_too_large", details="Uploaded file exceeds the configured maximum size."), 413

	startup_checks()
	return app
