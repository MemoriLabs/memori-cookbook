from app.models.agents import AgentType


def test_get_agent_types(client):
    """
    Test that we can retrieve all available agent types.
    """
    response = client.get("/api/v1/agents")

    assert response.status_code == 200

    data = response.json()
    assert "agents" in data
    assert "default" in data

    # Check we have all expected agents
    agent_types = [agent["type"] for agent in data["agents"]]
    assert AgentType.GENERAL.value in agent_types
    assert AgentType.PROGRAMMING.value in agent_types
    assert AgentType.CUSTOMER_SUPPORT.value in agent_types
    assert AgentType.FINANCE.value in agent_types

    # Check default is set
    assert data["default"] == AgentType.GENERAL.value


def test_agent_type_structure(client):
    """
    Test that each agent has the required fields.
    """
    response = client.get("/api/v1/agents")
    data = response.json()

    # Check first agent has all required fields
    first_agent = data["agents"][0]
    assert "type" in first_agent
    assert "name" in first_agent
    assert "description" in first_agent

    # Check fields are not empty
    assert len(first_agent["name"]) > 0
    assert len(first_agent["description"]) > 0


def test_agent_count(client):
    """
    Test that we have exactly 4 agents.

    If you add more agent types, update this test!
    """
    response = client.get("/api/v1/agents")
    data = response.json()

    assert len(data["agents"]) == 4
