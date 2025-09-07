import requests
import pytest


def test_audit_logs_requires_admin(base_url, headers, has_valid_api_key):
    if not has_valid_api_key:
        pytest.skip("No valid API key configured for live server")
    # With admin key we should get 200 and a list
    r = requests.get(f"{base_url}/admin/audit-logs", headers=headers, timeout=10)
    assert r.status_code in (200, 204), r.text
    if r.status_code == 200:
        assert isinstance(r.json(), list)
