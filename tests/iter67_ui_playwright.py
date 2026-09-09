"""Iter67 UI regression script (used in browser automation async context)."""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
from tests.support_config import FINANCE
load_dotenv("/app/frontend/.env")


STATE = json.loads(Path("/app/tests/iter67_ui_fixture_state.json").read_text(encoding="utf-8"))


async def run(page):
    label = STATE["label"]
    manager = STATE["manager"]
    label_id = label["id"]
    release_main_id = label["release_main_id"]
    base = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

    async def login(email, password):
        await page.goto(f"{base}/login", wait_until="domcontentloaded")
        await page.wait_for_timeout(300)
        await page.get_by_test_id("login-email-input").fill(email)
        await page.get_by_test_id("login-password-input").fill(password)
        await page.get_by_test_id("login-submit-button").click(force=True)
        await page.wait_for_timeout(1200)

    await page.set_viewport_size({"width": 1920, "height": 800})
    await login(FINANCE["email"], FINANCE["password"])
    await page.goto(f"{base}/admin/releases", wait_until="domcontentloaded")
    await page.wait_for_selector(f'[data-testid="admin-release-row-{release_main_id}"]', timeout=15000)
    await page.get_by_test_id(f"admin-release-isrc-toggle-{release_main_id}").click(force=True)
    await page.wait_for_selector(f'[data-testid="admin-release-isrc-panel-{release_main_id}"]', timeout=8000)
    await page.goto(f"{base}/admin/labels", wait_until="domcontentloaded")
    await page.wait_for_selector(f'[data-testid="admin-label-row-{label_id}"]', timeout=15000)
    await page.get_by_test_id(f"admin-label-detail-{label_id}").click(force=True)
    await page.wait_for_selector('[data-testid="admin-label-subscription-card"]', timeout=10000)
    await page.get_by_test_id("admin-label-sub-tier-select").select_option("annual_vip")
    await page.get_by_test_id("admin-label-sub-expiry-input").fill("2030-12-31")
    await page.get_by_test_id("admin-label-sub-reason").fill("Finance confirm package update iter67")
    await page.get_by_test_id("admin-label-sub-save").click(force=True)
    await page.wait_for_timeout(300)
    await page.get_by_test_id("admin-label-package-confirm-submit").click(force=True)
    await page.wait_for_timeout(1500)

    await login(manager["email"], manager["password"])
    await page.goto(f"{base}/admin/labels", wait_until="domcontentloaded")
    await page.wait_for_selector(f'[data-testid="admin-label-row-{label_id}"]', timeout=15000)
    await page.get_by_test_id(f"admin-label-detail-{label_id}").click(force=True)
    await page.wait_for_selector('[data-testid="admin-label-subscription-card"]', timeout=10000)
    await page.get_by_test_id("admin-label-sub-tier-select").select_option("pay_per_release")
    await page.get_by_test_id("admin-label-sub-reason").fill("Manager rollback to PPR iter67")
    await page.get_by_test_id("admin-label-sub-save").click(force=True)
    await page.wait_for_timeout(300)
    await page.get_by_test_id("admin-label-package-confirm-submit").click(force=True)
    await page.wait_for_timeout(1500)

    await login(label["email"], label["password"])
    await page.goto(f"{base}/label/releases", wait_until="domcontentloaded")
    await page.wait_for_selector(f'[data-testid="label-release-title-{release_main_id}"]', timeout=12000)