import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_openai_and_memori():
    with (
        patch("agents.base.OpenAI") as mock_oai,
        patch("agents.base.Memori") as mock_mem,
    ):
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices[0].message.content = "mocked response"
        fake_client.chat.completions.create.return_value = fake_response
        mock_oai.return_value = fake_client

        fake_mem_instance = MagicMock()
        fake_mem_instance.llm.register.return_value = MagicMock()
        mock_mem.return_value = fake_mem_instance

        yield fake_client, fake_mem_instance


def test_coder_agent_run(mock_openai_and_memori):
    from agents.coder import CoderAgent

    agent = CoderAgent()
    result = agent.run("Implement a login endpoint")
    assert result == "mocked response"


def test_reviewer_agent_chains_prior_context(mock_openai_and_memori):
    from agents.reviewer import ReviewerAgent

    fake_client, _ = mock_openai_and_memori
    agent = ReviewerAgent()
    agent.run(task="Review this", prior_context="Coder output here")

    call_args = fake_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    user_msg = next(m for m in messages if m["role"] == "user")
    assert "Prior agent output" in user_msg["content"]
    assert "Coder output here" in user_msg["content"]


def test_all_agents_share_process_id():
    from agents.coder import CoderAgent
    from agents.docs import DocsAgent
    from agents.reviewer import ReviewerAgent
    from agents.tester import TesterAgent

    # All agents use the same process_id so they share branch memory
    ids = {
        CoderAgent.PROCESS_ID,
        ReviewerAgent.PROCESS_ID,
        TesterAgent.PROCESS_ID,
        DocsAgent.PROCESS_ID,
    }
    assert len(ids) == 1, "All agents must share a single PROCESS_ID for mesh memory"


def test_git_context_id_includes_branch(fake_repo):
    import subprocess

    from core.git_context import get_context_id

    subprocess.run(
        ["git", "-C", fake_repo, "checkout", "-b", "feat/test-branch", "-q"],
        check=True,
    )
    context_id = get_context_id(fake_repo)
    assert "feat/test-branch" in context_id


def test_token_savings_demo_runs():
    from demos.token_savings import simulate_after, simulate_before

    before = simulate_before()
    after = simulate_after()

    assert len(before) == len(after)
    for b, a in zip(before, after, strict=True):
        # Memori approach must always use fewer tokens
        assert (
            a["tokens"] < b["tokens"]
        ), f"Session {b['session']}: after ({a['tokens']}) should be < before ({b['tokens']})"


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("MEMORI_API_KEY") or not os.getenv("GOOGLE_API_KEY"),
    reason="requires MEMORI_API_KEY and GOOGLE_API_KEY",
)
def test_memori_attribution_is_called_on_real_client():
    """Verify that Memori actually wraps the LLM client and sets attribution.

    This is the core mechanism the cookbook teaches: register → attribute → use.
    If this breaks, the memory mesh silently stops working.
    """

    from memori import Memori
    from openai import OpenAI

    from core.config import GEMINI_BASE_URL

    real_key = os.environ["GOOGLE_API_KEY"]
    client = OpenAI(api_key=real_key, base_url=GEMINI_BASE_URL)

    mem = Memori()
    registered = mem.llm.register(client)

    # attribution() must not raise — it sets the entity_id/process_id scope
    # that routes memories to the correct branch bucket
    registered.attribution(entity_id="test-repo/test-branch", process_id="memori-mesh")

    # Memori returns a handle for attribution; the original client is what agents
    # use for API calls — verify registration doesn't break it
    assert hasattr(
        client, "chat"
    ), "OpenAI client must still expose .chat after Memori registration"
    assert callable(client.chat.completions.create)
