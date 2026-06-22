import os
import subprocess

import pytest


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    # Tests mock OpenAI and Memori to avoid real API calls (see test_agents.py).
    # This keeps the suite fast and runnable without credentials.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("MEMORI_API_KEY", "test-memori-key")

    from core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_repo(tmp_path):
    """Minimal git repo for testing git_context utilities."""
    subprocess.run(["git", "init", str(tmp_path), "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"], check=True
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "--allow-empty", "-m", "init", "-q"],
        check=True,
    )
    return str(tmp_path)
