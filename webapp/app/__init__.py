"""LogLens Flask application factory."""

from flask import Flask

from app.routes import main


def create_app() -> Flask:
	"""Create and configure the Flask application."""
	app = Flask(__name__)
	app.register_blueprint(main)
	return app
