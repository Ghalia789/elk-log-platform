"""LogLens Flask application factory."""

import logging
import os

from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from app.clients import startup_checks
from app.routes import main
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
	app.register_blueprint(main)
	app.register_blueprint(upload)

	@app.errorhandler(RequestEntityTooLarge)
	def handle_request_entity_too_large(error):
		return jsonify(error="file_too_large", details="Uploaded file exceeds the configured maximum size."), 413

	startup_checks()
	return app
