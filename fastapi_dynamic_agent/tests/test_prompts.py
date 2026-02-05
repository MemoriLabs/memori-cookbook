from app.models.agents import AgentType
from app.prompts import AGENT_PROMPTS, get_system_prompt


def test_all_agent_types_have_prompts():
    """
    Ensure every AgentType has a corresponding prompt.
    """
    for agent_type in AgentType:
        assert agent_type in AGENT_PROMPTS
        assert len(AGENT_PROMPTS[agent_type]) > 0


def test_get_system_prompt_without_name():
    """
    Test getting a prompt without user name.
    """
    prompt = get_system_prompt(AgentType.GENERAL)

    assert len(prompt) > 0
    assert "AI assistant" in prompt
    assert "name is" not in prompt  # Should not have name


def test_get_system_prompt_with_name():
    """
    Test getting a prompt with user name.
    """
    prompt = get_system_prompt(AgentType.PROGRAMMING, user_name="Ryan")

    assert len(prompt) > 0
    assert "Ryan" in prompt
    assert "name is Ryan" in prompt


def test_different_agent_types_have_different_prompts():
    """
    Ensure each agent type has a unique prompt.
    """
    prompts = [
        get_system_prompt(AgentType.GENERAL),
        get_system_prompt(AgentType.PROGRAMMING),
        get_system_prompt(AgentType.CUSTOMER_SUPPORT),
        get_system_prompt(AgentType.FINANCE),
    ]

    # All prompts should be unique
    assert len(prompts) == len(set(prompts))
