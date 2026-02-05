from pydantic import BaseModel, Field

from app.models.agents import AgentType


class ChatRequest(BaseModel):
    """
    Chat request from the client.
    """

    q: str = Field(..., description="User's question or message", min_length=1)
    name: str | None = Field(None, description="User's name (optional)")
    agent_type: AgentType | None = Field(
        default=AgentType.GENERAL,
        description="Type of AI agent to use for this conversation",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "q": "What's my favorite color?",
                    "name": "Ryan",
                    "agent_type": "general",
                },
                {
                    "q": "How do I implement a binary search tree?",
                    "agent_type": "programming",
                },
            ]
        }
    }


class Message(BaseModel):
    """Single message in the conversation."""

    content: str = Field(..., description="Message content")
    role: str = Field(default="assistant", description="Message role")


class ChatResponse(BaseModel):
    """
    Chat response to the client.

    Includes the AI's response.
    """

    messages: list[Message] = Field(..., description="AI response messages")
    agent_type: AgentType = Field(..., description="Agent type used for this response")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "messages": [
                        {"content": "Your favorite color is blue!", "role": "assistant"}
                    ],
                    "agent_type": "general",
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
