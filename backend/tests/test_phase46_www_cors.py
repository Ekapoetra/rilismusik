"""Phase 46 — apex/www same-origin auth regression."""
from pathlib import Path

from server import expand_origin_variants


def test_custom_domain_expands_to_apex_and_www():
    assert expand_origin_variants(["https://rilismusik.com"]) == [
        "https://rilismusik.com", "https://www.rilismusik.com",
    ]
    assert expand_origin_variants(["https://www.rilismusik.com/"]) == [
        "https://www.rilismusik.com", "https://rilismusik.com",
    ]


def test_preview_subdomain_is_not_broadened():
    origin = "https://lanjut-core.preview.emergentagent.com"
    assert expand_origin_variants([origin]) == [origin]


def test_browser_client_always_uses_relative_api_and_files():
    source = Path("/app/frontend/src/api/client.js").read_text()
    assert 'export const API_BASE = IS_BROWSER ? "/api"' in source
    assert "return IS_BROWSER ? path" in source
    assert "window.location.origin" not in source