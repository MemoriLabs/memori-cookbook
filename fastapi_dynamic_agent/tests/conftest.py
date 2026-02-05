from unittest.mock import Mock, patch

import pytest
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI application.

    This fixture provides a client that can make HTTP requests
    to the application without starting an actual server.

    Usage:
        def test_something(client):
            response = client.get("/health")
            assert response.status_code == 200
    """
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_user_id():
    """
    Provide a consistent test user ID.

    Usage:
        def test_chat(test_user_id):
            assert test_user_id == "test-user-12345"
    """
    return "test-user-12345"


@pytest.fixture
def sample_chat_request():
    """
    Provide a sample chat request payload.

    Usage:
        def test_chat(client, test_user_id, sample_chat_request):
            response = client.post(
                f"/api/v1/chat/{test_user_id}",
                json=sample_chat_request
            )
    """
    return {"q": "Hello, how are you?", "name": "Test User"}


@pytest.fixture
def mock_openai_response():
    """
    Mock OpenAI API response.

    This prevents actual API calls during tests (saves money and time!).
    """
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "This is a test response from the AI"
    return mock_response


@pytest.fixture
def mock_memori():
    """
    Mock Memori service.

    This prevents actual Memori calls during tests.
    """
    with patch("app.services.llm.Memori") as mock:
        mock_instance = Mock()
        mock_instance.openai.register.return_value = mock_instance
        mock_instance.attribution.return_value = None
        mock.return_value = mock_instance
        yield mock_instance
