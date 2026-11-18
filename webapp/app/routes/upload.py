"""Upload and preview routes."""

import logging
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from app.services.validation import ValidationError, preview_content, validate_upload

logger = logging.getLogger(__name__)
upload = Blueprint("upload", __name__)


def _max_upload_bytes() -> int:
    return int(os.getenv("MAX_UPLOAD_MB", "100")) * 1024 * 1024


def _uploaded_file():
    uploaded_file = request.files.get("file")
    if uploaded_file is None or not uploaded_file.filename:
        raise ValidationError("missing_file", "A file is required in the 'file' form field.")
    return uploaded_file


def _read_upload(uploaded_file) -> bytes:
    content = uploaded_file.read(_max_upload_bytes() + 1)
    if len(content) > _max_upload_bytes():
        raise ValidationError(
            "file_too_large",
            f"File size must be at most {os.getenv('MAX_UPLOAD_MB', '100')} MB.",
            413,
        )
    return content


def _validation_error_response(error: ValidationError):
    return jsonify(error=error.message, details=error.details), error.status_code


@upload.get("/upload")
def upload_form():
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Upload logs - LogLens</title>
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; background: #f4f7fb; color: #172033; }
    nav { display: flex; align-items: center; gap: 1.25rem; padding: 1rem 2rem; background: #172033; }
    nav strong { color: white; margin-right: auto; }
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
    <h1>Upload logs</h1>
    <form method="post" action="/upload" enctype="multipart/form-data">
      <input type="file" name="file" required>
      <button type="submit">Submit</button>
    </form>
  </main>
</body>
</html>"""


@upload.post("/upload/preview")
def preview_upload():
    """
    Preview and validate a log file before upload.
    ---
    tags:
      - uploads
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: CSV, newline-delimited JSON, or TXT log file.
    produces:
      - application/json
    responses:
      200:
        description: Validated file metadata and preview lines.
      400:
        description: Invalid or unsupported upload.
      413:
        description: Uploaded file exceeds the configured size limit.
    """
    try:
        uploaded_file = _uploaded_file()
        content = _read_upload(uploaded_file)
        file_format = validate_upload(uploaded_file.filename, content, _max_upload_bytes())
        return jsonify(
            filename=uploaded_file.filename,
            format=file_format,
            lines=preview_content(content, file_format),
        )
    except ValidationError as error:
        return _validation_error_response(error)


@upload.post("/upload")
def save_upload():
    """
    Validate and atomically save a log file for Logstash ingestion.
    ---
    tags:
      - uploads
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: CSV, newline-delimited JSON, or TXT log file.
    produces:
      - application/json
    responses:
      202:
        description: Upload accepted and stored in the shared uploads volume.
      400:
        description: Invalid filename or unsupported file content.
      413:
        description: Uploaded file exceeds the configured size limit.
    """
    try:
        uploaded_file = _uploaded_file()
        content = _read_upload(uploaded_file)
        file_format = validate_upload(uploaded_file.filename, content, _max_upload_bytes())
        safe_name = secure_filename(uploaded_file.filename)
        if not safe_name:
            raise ValidationError("invalid_filename", "The uploaded filename is not valid.", 400)

        upload_id = f"u_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(2)}"
        upload_dir = Path(os.getenv("UPLOAD_DIR", "/uploads"))
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / f"{upload_id}__{safe_name}"

        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=upload_dir,
                prefix=f".{destination.name}.",
                suffix=".part",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.chmod(temporary_path, 0o644)
            os.replace(temporary_path, destination)
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

        logger.info(
            "Upload saved: upload_id=%s filename=%s size_bytes=%d format=%s path=%s",
            upload_id,
            safe_name,
            len(content),
            file_format,
            destination,
        )
        return jsonify(
            upload_id=upload_id,
            filename=safe_name,
            size_bytes=len(content),
            format=file_format,
        ), 202
    except ValidationError as error:
        return _validation_error_response(error)
