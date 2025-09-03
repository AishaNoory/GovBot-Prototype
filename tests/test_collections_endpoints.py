import requests
import pytest


def test_list_collections_ok(base_url, headers, has_valid_api_key):
    if not has_valid_api_key:
        pytest.skip("No valid API key configured for live server")
    r = requests.get(f"{base_url}/collection-stats/collections", headers=headers, timeout=10)
    assert r.status_code == 200, r.text
    arr = r.json()
    assert isinstance(arr, list)
    if arr:
        item = arr[0]
        assert "id" in item and "name" in item and "type" in item


def test_collection_stats_all_ok(base_url, headers, has_valid_api_key):
    if not has_valid_api_key:
        pytest.skip("No valid API key configured for live server")
    r = requests.get(f"{base_url}/collection-stats/", headers=headers, timeout=10)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), dict)
