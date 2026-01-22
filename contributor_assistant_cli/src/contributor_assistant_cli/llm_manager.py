"""Multi-LLM provider management."""

import os
from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def chat(self, messages: list[dict]) -> str:
        """Send a message and get a response."""
        pass

    @abstractmethod
    def get_client(self) -> Any:
        """Get the underlying client object."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""

    def __init__(self) -> None:
        """Initialize OpenAI provider."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    def chat(self, messages: list[dict]) -> str:
        """Send a message to OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=1024,
        )
        return response.choices[0].message.content

    def get_client(self) -> Any:
        """Get the OpenAI client."""
        return self.client


class AnthropicProvider(BaseLLMProvider):
    """Anthropic API provider."""

    def __init__(self) -> None:
        """Initialize Anthropic provider."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        from anthropic import Anthropic

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"

    def chat(self, messages: list[dict]) -> str:
        """Send a message to Anthropic."""
        response = self.client.messages.create(
            model=self.model,
            messages=messages,
            max_tokens=1024,
        )
        return response.content[0].text

    def get_client(self) -> Any:
        """Get the Anthropic client."""
        return self.client


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider."""

    def __init__(self) -> None:
        """Initialize Gemini provider."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel("gemini-2.0-flash")
        self.model = "gemini-2.0-flash"

    def chat(self, messages: list[dict]) -> str:
        """Send a message to Gemini."""
        response = self.client.generate_content(
            contents=[msg["content"] for msg in messages]
        )
        return response.text

    def get_client(self) -> Any:
        """Get the Gemini client."""
        return self.client


class XAIProvider(BaseLLMProvider):
    """xAI API provider."""

    def __init__(self) -> None:
        """Initialize xAI provider."""
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError("XAI_API_KEY environment variable not set")

        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        self.model = "grok-2"

    def chat(self, messages: list[dict]) -> str:
        """Send a message to xAI."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=1024,
        )
        return response.choices[0].message.content

    def get_client(self) -> Any:
        """Get the xAI client."""
        return self.client


class LLMManager:
    """Manage LLM provider selection and chat."""

    PROVIDERS = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "xai": XAIProvider,
    }

    def __init__(self, provider: str = "anthropic") -> None:
        """Initialize LLM manager with specified provider."""
        if provider not in self.PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {', '.join(self.PROVIDERS.keys())}"
            )

        try:
            self.provider_name = provider
            self.provider = self.PROVIDERS[provider]()
        except ValueError as e:
            raise ValueError(
                f"Failed to initialize {provider} provider: {str(e)}"
            ) from e

    def chat(self, messages: list[dict]) -> str:
        """Send a message and get a response."""
        return self.provider.chat(messages)

    def get_client(self) -> Any:
        """Get the underlying LLM client."""
        return self.provider.get_client()

    @staticmethod
    def get_available_providers() -> list[str]:
        """Get list of available LLM providers."""
        return list(LLMManager.PROVIDERS.keys())
