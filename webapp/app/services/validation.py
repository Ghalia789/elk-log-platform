"""Pure upload validation and preview parsing helpers."""

import csv
import io
import json
from dataclasses import dataclass
from typing import Any


EXPECTED_COLUMNS = (
    "timestamp",
    "level",
    "service",
    "endpoint",
    "http_method",
    "status_code",
    "response_time_ms",
    "client_ip",
    "user_id",
    "trace_id",
    "message",
)
SUPPORTED_FORMATS = {"csv", "json", "txt"}


@dataclass
class ValidationError(Exception):
    """A validation failure with an HTTP status and client-safe details."""

    message: str
    details: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.message


def get_format(filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in SUPPORTED_FORMATS:
        raise ValidationError(
            "unsupported_file_type",
            "File extension must be .csv, .json, or .txt.",
            415,
        )
    return extension


def validate_size(content: bytes, max_upload_bytes: int) -> None:
    if len(content) > max_upload_bytes:
        raise ValidationError(
            "file_too_large",
            f"File size must be at most {max_upload_bytes // (1024 * 1024)} MB.",
            413,
        )


def _decode_utf8(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("invalid_encoding", "File must be valid UTF-8.", 400) from exc


def validate_csv(content: bytes) -> None:
    text = _decode_utf8(content)
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next(reader, None)
        if not header:
            raise ValidationError("invalid_csv", "CSV file is empty.", 400)
        missing = [column for column in EXPECTED_COLUMNS if column not in header]
        if missing:
            raise ValidationError(
                "invalid_csv_header",
                f"CSV header is missing columns: {', '.join(missing)}.",
                400,
            )
        for row_number, row in enumerate(reader, start=2):
            if row_number > 101:
                break
            if len(row) != len(header):
                raise ValidationError(
                    "invalid_csv_rows",
                    f"CSV row {row_number} has {len(row)} columns; expected {len(header)}.",
                    400,
                )
    except csv.Error as exc:
        raise ValidationError("invalid_csv", "CSV parsing failed.", 400) from exc


def _parse_json(content: bytes) -> list[dict[str, Any]]:
    text = _decode_utf8(content)
    if not text.strip():
        raise ValidationError("invalid_json", "JSON file is empty.", 400)

    if text.lstrip().startswith("["):
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValidationError("invalid_json", "JSON array parsing failed.", 400) from exc
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise ValidationError("invalid_json", "JSON array must contain only objects.", 400)
        return value

    objects = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                "invalid_json",
                f"JSON line {line_number} is not valid JSON.",
                400,
            ) from exc
        if not isinstance(value, dict):
            raise ValidationError(
                "invalid_json",
                f"JSON line {line_number} must contain an object.",
                400,
            )
        objects.append(value)
    if not objects:
        raise ValidationError("invalid_json", "JSON file contains no objects.", 400)
    return objects


def validate_json(content: bytes) -> None:
    _parse_json(content)


def validate_txt(content: bytes) -> None:
    text = _decode_utf8(content)
    if not text.strip():
        raise ValidationError("invalid_text", "TXT file must not be empty.", 400)


def validate_upload(filename: str, content: bytes, max_upload_bytes: int) -> str:
    file_format = get_format(filename)
    validate_size(content, max_upload_bytes)
    if file_format == "csv":
        validate_csv(content)
    elif file_format == "json":
        validate_json(content)
    else:
        validate_txt(content)
    return file_format


def preview_content(content: bytes, file_format: str) -> list[Any]:
    """Return the first ten parsed records/lines after validation."""
    if file_format == "csv":
        text = _decode_utf8(content)
        reader = csv.DictReader(io.StringIO(text, newline=""))
        return [row for row in reader if row][:10]
    if file_format == "json":
        return _parse_json(content)[:10]
    return _decode_utf8(content).splitlines()[:10]
