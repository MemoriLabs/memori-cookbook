from unittest.mock import Mock, patch


def test_chat_endpoint_basic(client, test_user_id, sample_chat_request):
    """
    Test basic chat functionality with mocked services.
    """
    # Mock the OpenAI response
    mock_openai_response = Mock()
    mock_openai_response.choices = [Mock()]
    mock_openai_response.choices[
        0
    ].message.content = "Hello! I'm doing great, thanks for asking!"

    # Patch both OpenAI and Memori
    with (
        patch("app.services.llm.OpenAI") as mock_openai,
        patch("app.services.llm.Memori") as mock_memori,
    ):
        # Setup OpenAI mock
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_openai.return_value = mock_client

        # Setup Memori mock
        mock_mem_instance = Mock()
        mock_mem_instance.openai.register.return_value = mock_mem_instance
        mock_memori.return_value = mock_mem_instance

        # Make the request
        response = client.post(f"/api/v1/chat/{test_user_id}", json=sample_chat_request)

        # Verify response
        assert response.status_code == 200

        data = response.json()
        assert "messages" in data
        assert "agent_type" in data

        # Check message structure
        assert len(data["messages"]) > 0
        assert (
            data["messages"][0]["content"]
            == "Hello! I'm doing great, thanks for asking!"
        )
        assert data["messages"][0]["role"] == "assistant"

        # Verify Memori attribution was called
        mock_mem_instance.attribution.assert_called_once()


def test_chat_with_different_agent_types(client, test_user_id):
    """
    Test that different agent types can be used.
    """
    mock_openai_response = Mock()
    mock_openai_response.choices = [Mock()]
    mock_openai_response.choices[
        0
    ].message.content = "Here's how to write a function..."

    with (
        patch("app.services.llm.OpenAI") as mock_openai,
        patch("app.services.llm.Memori") as mock_memori,
    ):
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_openai.return_value = mock_client

        mock_mem_instance = Mock()
        mock_mem_instance.openai.register.return_value = mock_mem_instance
        mock_memori.return_value = mock_mem_instance

        # Test with programming agent
        response = client.post(
            f"/api/v1/chat/{test_user_id}",
            json={"q": "How do I write a function?", "agent_type": "programming"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["agent_type"] == "programming"


def test_chat_empty_message(client, test_user_id):
    """
    Test that empty messages are rejected.
    """
    response = client.post(f"/api/v1/chat/{test_user_id}", json={"q": ""})

    # Should return validation error (422 Unprocessable Entity)
    assert response.status_code == 422


def test_chat_missing_message(client, test_user_id):
    """
    Test that requests without the 'q' field are rejected.
    """
    response = client.post(f"/api/v1/chat/{test_user_id}", json={"name": "Test"})

    # Should return validation error
    assert response.status_code == 422


def test_chat_with_name(client, test_user_id):
    """
    Test that user name is handled correctly.
    """
    mock_openai_response = Mock()
    mock_openai_response.choices = [Mock()]
    mock_openai_response.choices[0].message.content = "Hello Ryan!"

    with (
        patch("app.services.llm.OpenAI") as mock_openai,
        patch("app.services.llm.Memori") as mock_memori,
    ):
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_openai.return_value = mock_client

        mock_mem_instance = Mock()
        mock_mem_instance.openai.register.return_value = mock_mem_instance
        mock_memori.return_value = mock_mem_instance

        response = client.post(
            f"/api/v1/chat/{test_user_id}", json={"q": "Hello!", "name": "Ryan"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) > 0


def test_chat_service_error(client, test_user_id, sample_chat_request):
    """
    Test that service errors are handled gracefully with 500 response.
    """
    from app.services.llm import LLMService

    # Patch the chat method on the LLMService class to raise an exception
    with patch.object(
        LLMService, "chat", side_effect=Exception("Database connection failed")
    ):
        response = client.post(f"/api/v1/chat/{test_user_id}", json=sample_chat_request)

        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Error processing chat request" in data["detail"]
