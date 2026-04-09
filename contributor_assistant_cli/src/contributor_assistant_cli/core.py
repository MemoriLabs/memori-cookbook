"""Core assistant logic for the contributor assistant."""

from contributor_assistant_cli.llm_manager import LLMManager
from contributor_assistant_cli.memory_manager import MemoryManager


class ContributorAssistant:
    """Main contributor assistant."""

    SYSTEM_PROMPT = """You are an expert assistant helping developers contribute to the Memori open-source project.

You have knowledge about:
- Memori's architecture (LLM adapters, storage layer, memory augmentation)
- Code quality standards (Ruff linter, 88-character lines, type hints)
- Testing patterns (pytest, unit tests, integration tests)
- Contribution guidelines (bug fixes, features, documentation)
- Git workflow and GitHub pull requests

When answering questions:
1. Consider the developer's contribution goals and interests
2. Reference specific code patterns from the Memori codebase
3. Provide practical, actionable advice
4. Maintain consistency with Memori's coding standards
5. Suggest testing approaches for any code changes

Be concise but helpful. Remember what the developer has told you about their interests and goals."""

    def __init__(
        self,
        llm_provider: str = "anthropic",
        entity_id: str | None = None,
        process_id: str = "memori-contributor",
    ) -> None:
        """
        Initialize the contributor assistant.

        Args:
            llm_provider: LLM provider to use (openai, anthropic, gemini, xai)
            entity_id: Unique identifier for the developer
            process_id: Process identifier for memory tracking
        """
        # Initialize LLM
        self.llm_manager = LLMManager(llm_provider)

        # Initialize Memori
        if entity_id is None:
            from contributor_assistant_cli.config import Config

            config = Config()
            entity_id = config.get("entity_id", "contributor-default")

        self.memory_manager = MemoryManager(
            llm_client=self.llm_manager.get_client(),
            entity_id=entity_id,
            process_id=process_id,
        )

    def ask(self, question: str) -> str:
        """
        Ask the assistant a question.

        Args:
            question: The question to ask

        Returns:
            The assistant's response
        """
        messages = [
            {
                "role": "user",
                "content": f"{self.SYSTEM_PROMPT}\n\nQuestion: {question}",
            }
        ]

        response = self.llm_manager.chat(messages)
        self.memory_manager.wait()

        return response

    def get_context(self) -> dict:
        """Get current context and stored facts."""
        facts = self.memory_manager.get_facts()
        return {
            "facts": facts,
            "session_id": self.memory_manager.get_session_id(),
        }
