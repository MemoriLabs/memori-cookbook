def test_health_check(client):
    """
    Test that the health check endpoint returns success.

    This is the simplest possible test - just verify the endpoint works.
    """
    # Make a GET request to /health
    response = client.get("/health")

    # Check the status code
    assert response.status_code == 200

    # Check the response data
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["version"] == "1.0.0"
