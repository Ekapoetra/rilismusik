"""Read-only Vercel entrypoint for the V13 UI preview branch.

The preview reads the same database as production, so it reuses the migration
preview guard in vercel_app.py: only login/logout/refresh may write, while
payments, uploads, emails, data changes and background jobs are rejected.
Production keeps vercel_production_app.py; never point main at this file.
"""
import os

os.environ["RILISMUSIK_DEPLOYMENT_MODE"] = "preview"

from vercel_app import app  # noqa: E402,F401
