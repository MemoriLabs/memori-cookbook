from pydantic import BaseModel, Field

from app.models.agents import AgentType


class ChatRequest(BaseModel):
    q: str = Field(..., description="User's question or message", min_length=1)
    name: str | None = Field(None, description="User's name (optional)")
    agent_type: AgentType | None = Field(
        default=AgentType.GENERAL,
        description="Type of AI agent to use for this conversation",
    )


class Message(BaseModel):
    content: str = Field(..., description="Message content")
    role: str = Field(default="assistant", description="Message role")


class ChatResponse(BaseModel):
    messages: list[Message] = Field(..., description="AI response messages")
    agent_type: AgentType = Field(..., description="Agent type used for this response")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
