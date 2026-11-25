"""Search parameter validation and Elasticsearch query construction."""

from datetime import datetime


def _date_value(value, name):
	if not value:
		return None
	try:
		return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
	except ValueError as error:
		raise ValueError(f"'{name}' must be an ISO 8601 date/time.") from error


def parse_search_params(args):
	def positive_int(name, default):
		value = args.get(name, default)
		try:
			parsed = int(value)
		except (TypeError, ValueError) as error:
			raise ValueError(f"'{name}' must be a positive integer.") from error
		if parsed < 1:
			raise ValueError(f"'{name}' must be a positive integer.")
		return parsed

	page = positive_int("page", 1)
	per_page = positive_int("per_page", 50)
	if per_page > 200:
		raise ValueError("'per_page' must be at most 200.")

	sort = args.get("sort", "timestamp")
	if sort not in {"timestamp", "level", "service"}:
		raise ValueError("'sort' must be timestamp, level, or service.")
	order = args.get("order", "desc")
	if order not in {"asc", "desc"}:
		raise ValueError("'order' must be asc or desc.")

	date_from = _date_value(args.get("from"), "from")
	date_to = _date_value(args.get("to"), "to")
	if date_from and date_to and datetime.fromisoformat(date_from) > datetime.fromisoformat(date_to):
		raise ValueError("'from' must be earlier than or equal to 'to'.")

	return {
		"q": args.get("q", "").strip(),
		"level": args.get("level", "").strip(),
		"service": args.get("service", "").strip(),
		"from": date_from,
		"to": date_to,
		"page": page,
		"per_page": per_page,
		"sort": sort,
		"order": order,
	}


def build_query(params):
	filters = []
	must = []
	if params.get("q"):
		must.append({"simple_query_string": {"query": params["q"], "fields": ["message"]}})
	for field in ("level", "service"):
		if params.get(field):
			filters.append({"term": {field: params[field]}})
	date_range = {}
	if params.get("from"):
		date_range["gte"] = params["from"]
	if params.get("to"):
		date_range["lte"] = params["to"]
	if date_range:
		filters.append({"range": {"@timestamp": date_range}})
	return {"bool": {"must": must, "filter": filters}}


def pagination_offset(params):
	return (params["page"] - 1) * params["per_page"]