"""Seed and cleanup helpers for Iteration 32 label-rate import UI tests."""
from __future__ import annotations

import csv
import io
import os
import sys
from pathlib import Path

import pymongo
from dotenv import load_dotenv
from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "backend" / ".env", override=True)
load_dotenv(ROOT / "frontend" / ".env", override=True)

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
PREFIX = "ITER32_UI"


def db():
    client = pymongo.MongoClient(MONGO_URL)
    return client[DB_NAME]


def _csv_bytes(rows, delimiter=","):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter)
    writer.writerow(["No.", "Nama Label", "Rate"])
    writer.writerows(rows)
    return buffer.getvalue().encode()


def _xlsx_bytes(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["No.", "Nama Label", "Rate"])
    for row in rows:
        sheet.append(row)
    out = io.BytesIO()
    workbook.save(out)
    workbook.close()
    return out.getvalue()


def make_files() -> None:
    target = ROOT / "tests"
    target.mkdir(parents=True, exist_ok=True)
    rows = [
        [1, f"{PREFIX} Alpha Records", 70],
        [2, f"PT. {PREFIX} Alpha Records", 70],
        [3, f"{PREFIX} Beta Music", 55],
        [4, f"{PREFIX} Missing", 40],
        [5, f"{PREFIX} Gamma", 65],
        [6, "", 20],
        [7, f"{PREFIX} Zeta", 30],
        [8, f"{PREFIX} Conflict", 40],
        [9, f"{PREFIX} Conflict", 50],
    ]
    (target / "iter32_valid.csv").write_bytes(_csv_bytes(rows))
    (target / "iter32_valid_semicolon.csv").write_bytes(_csv_bytes(rows, delimiter=";"))
    (target / "iter32_valid.xlsx").write_bytes(_xlsx_bytes(rows))
    (target / "iter32_invalid_headers.csv").write_text("No.,Label,Persen\n1,X,60\n", encoding="utf-8")
    (target / "iter32_empty.csv").write_text("", encoding="utf-8")
    (target / "iter32_unsupported.txt").write_text("not-supported", encoding="utf-8")
    print("files_created")


def cleanup_files() -> None:
    target = ROOT / "tests"
    for name in [
        "iter32_valid.csv",
        "iter32_valid_semicolon.csv",
        "iter32_valid.xlsx",
        "iter32_invalid_headers.csv",
        "iter32_empty.csv",
        "iter32_unsupported.txt",
    ]:
        path = target / name
        if path.exists():
            path.unlink()
    print("files_removed")


def seed() -> None:
    database = db()
    labels = [
        {
            "id": f"{PREFIX}-alpha",
            "label_name": f"PT. {PREFIX} Alpha Records",
            "royalty_percentage_default": 60,
            "balance_pending_idr": 60000,
            "balance_available_idr": 0,
        },
        {
            "id": f"{PREFIX}-beta1",
            "label_name": f"{PREFIX} Beta-Music",
            "royalty_percentage_default": 50,
            "balance_pending_idr": 0,
            "balance_available_idr": 0,
        },
        {
            "id": f"{PREFIX}-beta2",
            "label_name": f"{PREFIX} Beta Music",
            "royalty_percentage_default": 45,
            "balance_pending_idr": 0,
            "balance_available_idr": 0,
        },
        {
            "id": f"{PREFIX}-gamma",
            "label_name": f"{PREFIX} Gamma",
            "royalty_percentage_default": 50,
            "balance_pending_idr": 0,
            "balance_available_idr": 0,
        },
        {
            "id": f"{PREFIX}-zeta",
            "label_name": f"{PREFIX} Zeta",
            "royalty_percentage_default": 30,
            "balance_pending_idr": 0,
            "balance_available_idr": 0,
        },
    ]
    database.labels.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.labels.insert_many(labels)
    database.royalty_imports.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.royalty_lines.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.withdraw_requests.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.royalty_imports.insert_one({"id": f"{PREFIX}-import", "status": "published", "period": "2026-07"})
    database.royalty_lines.insert_one({
        "id": f"{PREFIX}-line",
        "import_id": f"{PREFIX}-import",
        "label_id": f"{PREFIX}-alpha",
        "status": "pending",
        "legacy_settled": False,
        "period": "2026-07",
        "revenue_eur": 10,
        "exchange_rate": 10000,
        "label_idr": 60000,
        "distributor_idr": 40000,
        "label_percentage_applied": 60,
    })
    database.withdraw_requests.insert_one({
        "id": f"{PREFIX}-withdraw",
        "label_id": f"{PREFIX}-gamma",
        "status": "requested",
        "legacy_import": False,
    })
    print("seeded")


def cleanup() -> None:
    database = db()
    batches = list(database.label_rate_imports.find({
        "$or": [
            {"filename": {"$regex": "iter32_", "$options": "i"}},
            {"rows.input_label_name": {"$regex": PREFIX}},
        ]
    }, {"_id": 0, "id": 1, "job_id": 1}))
    batch_ids = [item.get("id") for item in batches if item.get("id")]
    embedded_job_ids = [item.get("job_id") for item in batches if item.get("job_id")]
    database.label_rate_imports.delete_many({"id": {"$in": batch_ids}})

    job_ids = list(set(embedded_job_ids))
    if batch_ids:
        for row in database.migrate_jobs.find(
            {"kind": "label_rate_sync", "batch_id": {"$in": batch_ids}},
            {"_id": 0, "id": 1},
        ):
            if row.get("id"):
                job_ids.append(row["id"])
    job_ids = list(set(job_ids))
    if job_ids:
        database.balance_transactions.delete_many({"reference_id": {"$in": job_ids}})
        database.migrate_jobs.delete_many({"id": {"$in": job_ids}})
    database.royalty_percentage_history.delete_many({"label_id": {"$regex": f"^{PREFIX}"}})
    database.withdraw_requests.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.royalty_lines.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.royalty_imports.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.labels.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    print("cleaned")


if __name__ == "__main__":
    action = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if action == "seed":
        seed()
    elif action == "cleanup":
        cleanup()
    elif action == "files":
        make_files()
    elif action == "files_cleanup":
        cleanup_files()
    else:
        raise SystemExit("Usage: python iter32_seed_label_rate_ui.py [seed|cleanup|files|files_cleanup]")
