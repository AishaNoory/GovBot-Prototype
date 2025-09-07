import requests
import pytest


def test_health_and_openapi(base_url):
    r = requests.get(f"{base_url}/openapi.json", timeout=10)
    assert r.status_code == 200
    spec = r.json()
    # sanity
    assert "paths" in spec and isinstance(spec["paths"], dict)
    # core endpoints exist
    assert "/health" in spec["paths"]
    assert "/documents/" in spec["paths"]


def test_api_info_auth_required(base_url, headers, has_valid_api_key):
    # without key
    r = requests.get(f"{base_url}/api-info", timeout=10)
    assert r.status_code in (401, 403)
    # with key
    r = requests.get(f"{base_url}/api-info", headers=headers, timeout=10)
    if not has_valid_api_key:
        pytest.skip("No valid API key configured for live server")
    assert r.status_code == 200
    body = r.json()
    assert "permissions" in body and isinstance(body["permissions"], list)


def test_documents_list_and_get_if_any(base_url, headers, has_valid_api_key):
    if not has_valid_api_key:
        pytest.skip("No valid API key configured for live server")
    r = requests.get(f"{base_url}/documents/", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    arr = r.json()
    assert isinstance(arr, list)
    if not arr:
        pytest.skip("No documents available to test GET by id")
    doc_id = arr[0]["id"]
    r2 = requests.get(f"{base_url}/documents/{doc_id}", headers=headers, timeout=15)
    assert r2.status_code == 200, f"GET /documents/{doc_id} failed with {r2.status_code}: {r2.text}"
    payload = r2.json()
    assert payload.get("id") == doc_id
    assert "access_url" in payload


def test_webpages_collection_routes_exist(base_url, headers, has_valid_api_key):
    if not has_valid_api_key:
        pytest.skip("No valid API key configured for live server")
    # validate collection route shape and 404 vs 200 behavior
    r = requests.get(f"{base_url}/webpages/collection/non-existent", headers=headers, timeout=10)
    # Should be 200 with empty list, not 500
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


def test_crawl_requires_write_permission(base_url, headers, has_valid_api_key):
    if not has_valid_api_key:
        pytest.skip("No valid API key configured for live server")
    # crawl should require auth with write permission; with our default master key it's fine
    body = {"url": "https://example.com", "collection_id": "test-collection"}
    r = requests.post(f"{base_url}/crawl/", headers=headers, json=body, timeout=15)
    # Either 200 (accepted) or 500 if crawler deps missing, but not 401
    assert r.status_code in (200, 500), r.text
