import requests
import pytest


def test_chat_history_not_found(base_url, headers, has_valid_api_key):
    if not has_valid_api_key:
        pytest.skip("No valid API key configured for live server")
    r = requests.get(f"{base_url}/chat/non-existent-session", headers=headers, timeout=10)
    assert r.status_code == 404


@pytest.mark.timeout(30)
@pytest.mark.skip(reason="Chat agent may require external model credentials; enable when configured")
def test_chat_process_minimal_roundtrip(base_url, headers):
    payload = {"message": "Hello"}
    r = requests.post(f"{base_url}/chat/", headers=headers, json=payload, timeout=25)
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data and "answer" in data
