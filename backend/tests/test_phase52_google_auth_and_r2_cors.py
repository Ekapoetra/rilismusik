"""Phase 52 — Google existing-label exchange and production R2 preflight."""
import asyncio
import os
import uuid

import requests
from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.responses import Response
from starlette.requests import Request


load_dotenv("/app/backend/.env", override=True)


def _request(host="www.rilismusik.com", origin="https://www.rilismusik.com"):
    return Request({
        "type": "http", "method": "POST", "path": "/api/auth/google/session",
        "headers": [(b"host", host.encode()), (b"origin", origin.encode())],
        "client": ("127.0.0.1", 12345),
    })


def test_google_exchange_allows_existing_label_only_and_is_single_use(monkeypatch):
    from routes import auth as module

    async def scenario():
        suffix = uuid.uuid4().hex[:10]
        user_id = f"phase52-user-{suffix}"
        label_id = f"phase52-label-{suffix}"
        email = f"phase52-{suffix}@example.com"
        session_id = f"phase52-session-{suffix}"

        async def fake_provider(_session_id):
            assert _session_id == session_id
            return {
                "id": f"google-{suffix}", "email": email, "name": "Phase 52 Google",
                "picture": "https://example.com/avatar.png", "email_verified": True,
                "session_token": f"provider-secret-{suffix}",
            }

        monkeypatch.setattr(module, "fetch_google_session_data", fake_provider)
        await module.db.users.insert_one({
            "id": user_id, "name": "Phase 52", "email": email, "password_hash": "unused",
            "role": "label", "status": "active", "token_version": 2,
            "email_verified_at": None, "created_at": "2026-09-01T00:00:00+00:00",
        })
        await module.db.labels.insert_one({
            "id": label_id, "user_id": user_id, "label_name": "Phase 52 Label",
            "account_status": "active", "created_at": "2026-09-01T00:00:00+00:00",
        })
        try:
            response = Response()
            result = await module.google_session_login(
                module.GoogleSessionIn(session_id=session_id), response, _request(),
            )
            assert result["user"]["id"] == user_id
            assert result["user"]["role"] == "label"
            assert result["label"]["id"] == label_id
            cookies = [value.decode() for key, value in response.raw_headers if key.lower() == b"set-cookie"]
            assert any(value.startswith("access_token=") and "HttpOnly" in value for value in cookies)
            assert any(value.startswith("refresh_token=") and "HttpOnly" in value for value in cookies)
            user = await module.db.users.find_one({"id": user_id}, {"_id": 0})
            assert user["email_verified_at"]
            assert user["google_provider_id"] == f"google-{suffix}"
            session = await module.db.google_auth_sessions.find_one({"user_id": user_id}, {"_id": 0})
            assert session["request_origin"] == "https://www.rilismusik.com"
            assert session.get("provider_session_token_hash")
            assert "session_token" not in session
            try:
                await module.google_session_login(
                    module.GoogleSessionIn(session_id=session_id), Response(), _request(),
                )
                raise AssertionError("Replay should fail")
            except HTTPException as exc:
                assert exc.status_code == 409
        finally:
            await module.db.google_auth_sessions.delete_many({"user_id": user_id})
            await module.db.activity_logs.delete_many({"actor_user_id": user_id})
            await module.db.labels.delete_one({"id": label_id})
            await module.db.users.delete_one({"id": user_id})

    asyncio.run(scenario())


def test_auth_email_links_only_trust_same_https_origin():
    from routes import auth as module

    assert module._trusted_request_origin(_request()) == "https://www.rilismusik.com"
    assert module._trusted_request_origin(_request(origin="https://evil.example")) is None
    assert module._trusted_request_origin(_request(origin="http://www.rilismusik.com")) is None


def test_r2_preflight_allows_apex_and_www_and_preserves_preview_origin():
    import storage_service

    async def scenario():
        origins = [
            "https://lanjut-core.preview.emergentagent.com",
            "https://rilismusik.com", "https://www.rilismusik.com",
        ]
        await storage_service.ensure_cors(origins)
        config = await storage_service.get_cors_config()
        allowed = set()
        for rule in (config or {}).get("CORSRules", []):
            allowed.update(rule.get("AllowedOrigins", []))
        assert set(origins).issubset(allowed)
        url = await storage_service.generate_presigned_put_url(
            key=f"cors-check/{uuid.uuid4().hex}.csv", content_type="text/csv", ttl=600,
        )
        for origin in ("https://rilismusik.com", "https://www.rilismusik.com"):
            response = requests.options(url, headers={
                "Origin": origin, "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "content-type",
            }, timeout=30)
            assert response.status_code in (200, 204)
            assert response.headers.get("Access-Control-Allow-Origin") in (origin, "*")

    asyncio.run(scenario())