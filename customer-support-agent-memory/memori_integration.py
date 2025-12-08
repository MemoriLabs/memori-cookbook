"""
Memori Integration

This module provides integration with Memori for persistent conversation memory.
Uses direct database integration with DigitalOcean Gradient AI agents.

Key Features:
- Direct DigitalOcean Gradient AI agent integration
- Automatic conversation tracking and recall
- Entity (user) and Process (agent) attribution
- Background fact extraction and augmentation
- Semantic search across conversation history
"""

import os
from typing import Any

from memori import Memori
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class MemoriIntegration:
    """Manages Memori integration for customer support agent with DigitalOcean Gradient AI"""

    def __init__(
        self,
        database_url: str | None = None,
        agent_endpoint: str | None = None,
        agent_access_key: str | None = None,
    ):
        """
        Initialize Memori integration with database and DigitalOcean Gradient AI agent.

        Args:
            database_url: PostgreSQL connection string for Memori storage
            agent_endpoint: DigitalOcean Gradient AI agent endpoint URL
            agent_access_key: DigitalOcean Gradient AI agent access key
        """
        # Setup database connection
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://do_user:do_user_password@localhost:5432/customer_support",
        )

        # Create SQLAlchemy engine and session factory
        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Setup DigitalOcean Gradient AI client (OpenAI-compatible)
        self.agent_endpoint = agent_endpoint
        self.agent_access_key = agent_access_key

        # Track current attribution to avoid resetting per message
        self._current_user_id: str | None = None
        self._current_process_id: str | None = None

        # Cache registered OpenAI clients per endpoint to maintain memory continuity
        self._registered_clients: dict[str, OpenAI] = {}

        # Note: OpenAI client will be created per-request with agent-specific credentials
        # Initialize Memori with database connection only
        self.mem = Memori(conn=self.SessionLocal)

        # Build database schema (idempotent - safe to call multiple times)
        try:
            self.mem.config.storage.build()
            print("INFO: Memori database schema initialized successfully")
        except Exception as e:
            print(f"WARNING: Memori schema initialization: {e}")

    def set_context(self, user_id: str, domain_id: str | None = None):
        """
        Set the attribution context for conversations.

        Args:
            user_id: Unique identifier for the user (entity)
            domain_id: Optional domain identifier for process attribution

        This should be called before each conversation to properly attribute memories.
        Only resets attribution if user or process changes.
        """
        # Create process_id from domain or use default
        process_id = f"support-agent-{domain_id}" if domain_id else "support-agent"

        # Only set attribution if it's different from current
        # This prevents resetting the context mid-conversation
        if self._current_user_id != user_id or self._current_process_id != process_id:
            self.mem.attribution(entity_id=user_id, process_id=process_id)
            self._current_user_id = user_id
            self._current_process_id = process_id
            print(
                f"DEBUG: Memori context updated - user: {user_id}, process: {process_id}"
            )
        else:
            print(
                f"DEBUG: Memori context unchanged - user: {user_id}, process: {process_id}"
            )

    def chat(
        self,
        question: str,
        user_id: str,
        domain_id: str | None = None,
        agent_url: str | None = None,
        agent_access_key: str | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a message and get a response with automatic memory integration.

        Args:
            question: User's question/message
            user_id: Unique identifier for the user
            domain_id: Optional domain identifier
            agent_url: DigitalOcean Gradient AI agent endpoint
            agent_access_key: DigitalOcean Gradient AI agent access key
            system_prompt: Optional system prompt to guide the assistant

        Returns:
            Dictionary with:
                - success: bool indicating success
                - answer: str with the AI response
                - error: str with error message (if failed)
        """
        try:
            # Use provided credentials or fall back to instance defaults
            endpoint = agent_url or self.agent_endpoint
            access_key = agent_access_key or self.agent_access_key

            if not endpoint or not access_key:
                raise ValueError("Agent endpoint and access key are required")

            # Ensure endpoint has proper format
            base_url = (
                endpoint if endpoint.endswith("/api/v1/") else f"{endpoint}/api/v1/"
            )

            # Set context for this conversation BEFORE creating/getting client
            # This is critical for proper memory attribution
            self.set_context(user_id, domain_id)

            # Get or create cached client for this endpoint
            # Reusing the same client is essential for Memori to maintain memory continuity
            client_key = f"{base_url}:{access_key[:10]}"  # Use endpoint + key prefix as cache key

            if client_key not in self._registered_clients:
                # Create new client and register with Memori
                client = OpenAI(base_url=base_url, api_key=access_key)
                self.mem.openai.register(client)
                self._registered_clients[client_key] = client
                print(f"DEBUG: Created and registered new OpenAI client for {base_url}")
            else:
                client = self._registered_clients[client_key]
                print(f"DEBUG: Reusing registered OpenAI client for {base_url}")

            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": question})

            # Call Gradient AI agent with Memori integration
            # Memori automatically handles memory recall and storage
            response = client.chat.completions.create(
                model="n/a",  # Model is determined by the Gradient agent
                messages=messages,
            )

            # Extract answer
            answer = response.choices[0].message.content

            print(f"DEBUG: Memori chat successful - {len(answer)} chars response")

            return {"success": True, "answer": answer}

        except Exception as e:
            error_msg = f"Memori chat error: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {"success": False, "error": error_msg}

    def recall_facts(
        self, query: str, user_id: str, domain_id: str | None = None, limit: int = 5
    ) -> dict[str, Any]:
        """
        Search for relevant facts from conversation history.

        Args:
            query: Search query
            user_id: User identifier to search facts for
            domain_id: Optional domain identifier
            limit: Maximum number of facts to return

        Returns:
            Dictionary with:
                - success: bool indicating success
                - facts: list of fact dictionaries
                - count: number of facts found
        """
        try:
            # Set context
            process_id = f"support-agent-{domain_id}" if domain_id else "support-agent"
            self.mem.attribution(entity_id=user_id, process_id=process_id)

            # Recall facts using semantic search
            facts = self.mem.recall(query, limit=limit)

            print(f"DEBUG: Recalled {len(facts)} facts for query: {query}")

            return {"success": True, "facts": facts, "count": len(facts)}

        except Exception as e:
            error_msg = f"Fact recall error: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {"success": False, "error": error_msg, "facts": [], "count": 0}

    def new_session(self) -> str:
        """
        Start a new session for conversation tracking.

        Returns:
            New session ID (UUID)
        """
        self.mem.new_session()
        session_id = str(self.mem.config.session_id)
        print(f"DEBUG: New Memori session created: {session_id}")
        return session_id

    def clear_client_cache(self):
        """
        Clear the cached OpenAI clients.
        Useful when you need to force recreation of clients (e.g., after credential changes).
        """
        self._registered_clients.clear()
        print("DEBUG: Cleared OpenAI client cache")


# Singleton instance for global access
_memori_instance: MemoriIntegration | None = None


def get_memori_instance(
    database_url: str | None = None,
    agent_endpoint: str | None = None,
    agent_access_key: str | None = None,
) -> MemoriIntegration:
    """
    Get or create the global Memori integration instance.

    Args:
        database_url: PostgreSQL connection string
        agent_endpoint: DigitalOcean Gradient AI agent endpoint (optional, can be provided per-request)
        agent_access_key: DigitalOcean Gradient AI agent access key (optional, can be provided per-request)

    Returns:
        MemoriIntegration instance
    """
    global _memori_instance

    if _memori_instance is None:
        _memori_instance = MemoriIntegration(
            database_url=database_url,
            agent_endpoint=agent_endpoint,
            agent_access_key=agent_access_key,
        )

    return _memori_instance
