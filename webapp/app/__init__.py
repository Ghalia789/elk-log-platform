"""LogLens Flask application factory."""

import logging
import os

from flask import Flask

from app.clients import startup_checks
from app.routes import main


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
	app.register_blueprint(main)
	startup_checks()
	return app
