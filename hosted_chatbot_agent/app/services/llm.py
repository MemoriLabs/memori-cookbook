"""
LLM Service with Memori Integration.

This service wraps the OpenAI client with Memori's memory enhancement.
"""

import logging

from memori import Memori
from openai import OpenAI

from app.core.config import get_settings
from app.models.agents import AgentType
from app.prompts import get_system_prompt

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM service with automatic memory enhancement via Memori.
    """

    def __init__(self):
        """Initialize the LLM client with Memori memory enhancement."""
        settings = get_settings()

        # Create OpenAI client
        self.client = OpenAI(api_key=settings.openai_api_key)

        # Wrap with Memori - this is where the magic happens!
        self.mem = Memori().openai.register(self.client)

        # Store model for configurability (AGENTS.md: stay LLM-agnostic)
        self.model = settings.openai_model

    def chat(
        self,
        user_id: str,
        message: str,
        user_name: str | None = None,
        agent_type: AgentType = AgentType.GENERAL,
    ) -> str:
        """
        Send a chat message and get a response with memory.

        Performance note: Makes 1 OpenAI API call. Memory retrieval
        and storage happen automatically in the background via Memori.

        Args:
            user_id: Unique identifier to isolate this user's memories
            message: The user's message
            user_name: Optional user name for personalization
            agent_type: Type of agent personality to use

        Returns:
            AI response text with memory context

        Raises:
            Exception: If there's an error with the LLM or Memori service
        """
        try:
            # Tell Memori who this conversation is for
            # This ensures memories are isolated per user
            self.mem.attribution(
                entity_id=user_id, process_id=f"demo-{agent_type.value}"
            )

            # Get the system prompt for this agent type
            system_prompt = get_system_prompt(agent_type, user_name)

            # Make the LLM call - Memori handles memory automatically
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=0.7,
                max_tokens=500,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            # Log with full context for debugging (AGENTS.md: meaningful exceptions)
            logger.error(
                f"Error in chat for user {user_id} with agent {agent_type.value}: {e}",
                exc_info=True,
            )
            raise

    def close(self):
        """Clean up resources if needed."""
        pass


# Singleton pattern for service instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """
    Get the singleton LLM service instance.

    Using a singleton ensures we don't create multiple Memori
    connections unnecessarily.
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
