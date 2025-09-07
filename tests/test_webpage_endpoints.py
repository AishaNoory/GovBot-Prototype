import requests
import pytest


def test_webpage_by_url_not_found_returns_404_or_200(base_url, headers, has_valid_api_key):
    if not has_valid_api_key:
        pytest.skip("No valid API key configured for live server")
    # Use an unlikely URL to exist in DB; API should return 404, not 500
    url = "https://example.com/this-page-should-not-exist-in-db"
    r = requests.get(f"{base_url}/webpages/by-url/", params={"url": url}, headers=headers, timeout=10)
    assert r.status_code in (200, 404), r.text
    if r.status_code == 200:
        body = r.json()
        assert "url" in body and isinstance(body["url"], str)
