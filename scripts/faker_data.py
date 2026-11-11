"""Generate realistic SaaS web application logs."""

import argparse
import csv
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from faker import Faker


LOG_FIELDS = (
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

SERVICES = ("api", "auth", "billing", "worker", "search")
SERVICE_WEIGHTS = (0.42, 0.18, 0.12, 0.10, 0.18)
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
LEVEL_WEIGHTS = (0.08, 0.70, 0.15, 0.06, 0.01)
ENDPOINTS = {
	"api": (("/api/v1/users", "GET"), ("/api/v1/events", "POST")),
	"auth": (("/api/v1/login", "POST"), ("/api/v1/token/refresh", "POST")),
	"billing": (("/api/v1/invoices", "GET"), ("/api/v1/payments", "POST")),
	"worker": (("/internal/jobs", "POST"), ("/internal/jobs/{id}", "GET")),
	"search": (("/api/v1/search", "GET"), ("/api/v1/search/suggestions", "GET")),
}
ERROR_STATUS_CODES = (500, 502, 503, 504)
SUCCESS_STATUS_CODES = (200, 201, 202, 204)
CLIENT_ERROR_STATUS_CODES = (400, 401, 403, 404, 429)


def choose_status_code(level: str, faker: Faker) -> int:
	"""Choose an HTTP status with server errors correlated to log severity."""
	if level == "CRITICAL":
		return faker.random_element(ERROR_STATUS_CODES)
	if level == "ERROR":
		return faker.random_element(elements=ERROR_STATUS_CODES if faker.random_int(1, 100) <= 80 else CLIENT_ERROR_STATUS_CODES)
	if level == "WARNING":
		return faker.random_element(elements=CLIENT_ERROR_STATUS_CODES if faker.random_int(1, 100) <= 65 else SUCCESS_STATUS_CODES)
	return faker.random_element(SUCCESS_STATUS_CODES)


def build_log_record(faker: Faker) -> dict[str, object]:
	"""Build a single SaaS application log record."""
	level = random.choices(LEVELS, weights=LEVEL_WEIGHTS, k=1)[0]
	service = random.choices(SERVICES, weights=SERVICE_WEIGHTS, k=1)[0]
	endpoint, http_method = faker.random_element(ENDPOINTS[service])
	status_code = choose_status_code(level, faker)
	response_time = faker.random_int(min=20, max=250 if status_code < 500 else 2500)
	timestamp = faker.date_time_between(
		start_date="-7d",
		end_date="now",
		tzinfo=timezone.utc,
	).isoformat()

	if status_code >= 500:
		message = f"{service} request failed with upstream status {status_code}"
	elif status_code >= 400:
		message = f"{service} request rejected with status {status_code}"
	elif level == "DEBUG":
		message = f"{service} request completed successfully"
	else:
		message = f"{service} request processed"

	return {
		"timestamp": timestamp,
		"level": level,
		"service": service,
		"endpoint": endpoint,
		"http_method": http_method,
		"status_code": status_code,
		"response_time_ms": response_time,
		"client_ip": faker.ipv4(),
		"user_id": f"user_{faker.uuid4(cast_to=None)}",
		"trace_id": faker.uuid4(cast_to=None).replace("-", ""),
		"message": message,
	}


def write_logs(records: list[dict[str, object]], output: TextIO, output_format: str) -> None:
	"""Write records as CSV or newline-delimited JSON."""
	if output_format == "csv":
		writer = csv.DictWriter(output, fieldnames=LOG_FIELDS)
		writer.writeheader()
		writer.writerows(records)
		return

	for record in records:
		output.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--count", type=int, default=10000, help="number of logs to generate (default: 10000)")
	parser.add_argument("--format", choices=("csv", "json"), default="json", help="output format (default: json)")
	parser.add_argument("--output", required=True, help="output path; use '-' for stdout")
	args = parser.parse_args()
	if args.count < 1:
		parser.error("--count must be at least 1")
	return args


def main() -> None:
	args = parse_args()
	faker = Faker()
	records = [build_log_record(faker) for _ in range(args.count)]

	if args.output == "-":
		write_logs(records, sys.stdout, args.format)
		return

	output_path = Path(args.output)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	with output_path.open("w", encoding="utf-8", newline="") as output:
		write_logs(records, output, args.format)


if __name__ == "__main__":
	main()
