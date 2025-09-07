import os
import time
import requests
import pytest
from dotenv import load_dotenv, find_dotenv


@pytest.fixture(scope="session")
def base_url():
	# Load environment variables from .env files (repo root preferred)
	# This allows tests to read GOVSTACK_API_KEY and GOVSTACK_BASE_URL from .env
	env_path = find_dotenv(usecwd=True)
	if env_path:
		load_dotenv(env_path)  # load root .env if present
	# Additionally try test-specific env files without failing if missing
	load_dotenv(os.path.join(os.path.dirname(__file__), ".env.external"), override=False)
	load_dotenv(os.path.join(os.path.dirname(__file__), ".env.test"), override=False)

	# Default to the provided external API base if not overridden
	return os.getenv("GOVSTACK_BASE_URL", "https://govstack-api.think.ke").rstrip("/")


@pytest.fixture(scope="session")
def headers():
	# After dotenv load, pick API key from env (GOVSTACK_API_KEY preferred)
	api_key = (
		os.getenv("GOVSTACK_API_KEY")
		or os.getenv("GOVSTACK_TEST_API_KEY")
		or os.getenv("GOVSTACK_ADMIN_API_KEY")
		or "gs-dev-master-key-12345"
	)
	return {"X-API-Key": api_key}


@pytest.fixture(scope="session", autouse=True)
def ensure_health(base_url):
	deadline = time.time() + 20
	last_err = None
	while time.time() < deadline:
		try:
			r = requests.get(f"{base_url}/health", timeout=3)
			if r.status_code == 200:
				return
		except Exception as e:
			last_err = e
		time.sleep(0.5)
	pytest.skip(f"API not healthy at {base_url}/health: {last_err}")


@pytest.fixture(scope="session")
def has_valid_api_key(base_url, headers):
	try:
		r = requests.get(f"{base_url}/api-info", headers=headers, timeout=5)
		return r.status_code == 200
	except Exception:
		return False
