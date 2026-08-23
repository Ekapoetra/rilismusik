"""Seed/cleanup utility for iter30 royalty repair-source UI verification."""
import csv
import io
import json
import os
import sys
import uuid
from pathlib import Path

import pymongo
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

sys.path.append("/app/backend")
import storage_service  # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
CONTEXT_PATH = Path("/app/tests/iter30_seed_context.json")
UPLOAD_DIR = Path("/app/backend/uploads/csv")
TEST_UPLOAD_FILE = Path("/app/tests/iter30_repair_source.csv")


def _db():
    client = pymongo.MongoClient(MONGO_URL)
    return client[DB_NAME]


def _build_csv_text():
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Bulan laporan", "Bulan Penjualan", "Nama Label", "Pendapatan Bersih"])
    writer.writerow(["01/04/2025", "01/01/2025", "TEST ITER30", "1,00"])
    writer.writerow(["01/05/2025", "01/02/2025", "TEST ITER30", "2,00"])
    return buffer.getvalue()


def seed():
    db = _db()
    import_id = f"TEST_ITER30_REPAIR_{uuid.uuid4().hex[:8]}"

    db.royalty_imports.insert_one({
        "id": import_id,
        "filename": "APRIL 2025.csv",
        "status": "dana_received",
        "period": "multi",
        "period_start": "2025-01",
        "period_end": "2025-02",
        "period_breakdown": {"2025-01": 1, "2025-02": 1},
        "uploaded_by": "iter30-ui-seed",
        "period_repair_status": "error",
        "period_repair_error": "RuntimeError: CSV asli tidak tersedia di disk maupun R2; upload ulang diperlukan.",
    })
    db.royalty_lines.insert_many([
        {
            "id": f"{import_id}-1", "import_id": import_id, "period": "2025-01",
            "row_period": "2025-01", "status": "available", "match_status": "matched",
            "label_idr": 10000, "revenue_eur": 1,
        },
        {
            "id": f"{import_id}-2", "import_id": import_id, "period": "2025-02",
            "row_period": "2025-02", "status": "available", "match_status": "matched",
            "label_idr": 20000, "revenue_eur": 2,
        },
    ])

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / f"{import_id}.csv").write_text("old-period-data", encoding="utf-8")
    TEST_UPLOAD_FILE.write_text(_build_csv_text(), encoding="utf-8")

    CONTEXT_PATH.write_text(json.dumps({"import_id": import_id, "csv_path": str(TEST_UPLOAD_FILE)}), encoding="utf-8")
    print(json.dumps({"import_id": import_id, "csv_path": str(TEST_UPLOAD_FILE)}))


def cleanup():
    db = _db()
    import_ids = [doc["id"] for doc in db.royalty_imports.find(
        {"id": {"$regex": "^TEST_ITER30_REPAIR_"}}, {"_id": 0, "id": 1}
    )]
    if CONTEXT_PATH.exists():
        context = json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
        if context.get("import_id") and context["import_id"] not in import_ids:
            import_ids.append(context["import_id"])
    if not import_ids:
        TEST_UPLOAD_FILE.unlink(missing_ok=True)
        CONTEXT_PATH.unlink(missing_ok=True)
        print(json.dumps({"cleanup": "nothing_to_delete"}))
        return

    object_keys = [doc.get("object_key") for doc in db.royalty_import_repair_uploads.find(
        {"import_id": {"$in": import_ids}}, {"_id": 0, "object_key": 1}
    ) if doc.get("object_key")]
    if storage_service.is_configured():
        import asyncio
        for key in object_keys:
            asyncio.run(storage_service.delete_object(key=key))

    db.royalty_import_repair_uploads.delete_many({"import_id": {"$in": import_ids}})
    db.migrate_jobs.delete_many({"import_id": {"$in": import_ids}})
    db.royalty_lines.delete_many({"import_id": {"$in": import_ids}})
    db.royalty_imports.delete_many({"id": {"$in": import_ids}})

    for import_id in import_ids:
        (UPLOAD_DIR / f"{import_id}.csv").unlink(missing_ok=True)
        (UPLOAD_DIR / f"{import_id}.csv.gz").unlink(missing_ok=True)
    TEST_UPLOAD_FILE.unlink(missing_ok=True)
    CONTEXT_PATH.unlink(missing_ok=True)
    print(json.dumps({"cleanup": "done", "import_ids": import_ids, "r2_deleted": storage_service.is_configured()}))


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "seed"
    if action == "seed":
        seed()
    elif action == "cleanup":
        cleanup()
    else:
        raise SystemExit(f"Unknown action: {action}")