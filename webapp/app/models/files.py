"""MongoDB operations for uploaded file metadata."""

from datetime import datetime, timezone

from app.clients import get_mongo_db


def create_file(upload_id, filename, stored_path, size_bytes, format):
	document = {
		"upload_id": upload_id,
		"filename": filename,
		"stored_path": stored_path,
		"size_bytes": size_bytes,
		"format": format,
		"status": "pending",
		"uploaded_at": datetime.now(timezone.utc),
		"log_count": 0,
	}
	get_mongo_db().files.insert_one(document)
	return document


def get_file(upload_id):
	return get_mongo_db().files.find_one({"upload_id": upload_id})


def list_files(page, per_page, status=None, date_from=None, date_to=None):
	query = {}
	if status:
		query["status"] = status
	if date_from or date_to:
		query["uploaded_at"] = {}
		if date_from:
			query["uploaded_at"]["$gte"] = date_from
		if date_to:
			query["uploaded_at"]["$lte"] = date_to

	collection = get_mongo_db().files
	items = list(
		collection.find(query)
		.sort("uploaded_at", -1)
		.skip((page - 1) * per_page)
		.limit(per_page)
	)
	return {"items": items, "total": collection.count_documents(query), "page": page, "per_page": per_page}


def update_status(upload_id, status, log_count):
	return get_mongo_db().files.update_one(
		{"upload_id": upload_id},
		{"$set": {"status": status, "log_count": log_count}},
	)