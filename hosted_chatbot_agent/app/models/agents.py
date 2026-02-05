from enum import Enum

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """
    Types of AI agents available.

    Each agent has a specialized personality and knowledge base.
    """

    GENERAL = "general"
    PROGRAMMING = "programming"
    CUSTOMER_SUPPORT = "customer_support"
    FINANCE = "finance"


class AgentTypeInfo(BaseModel):
    """
    Information about an agent type.
    """

    type: AgentType = Field(..., description="Agent type identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="What this agent specializes in")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "programming",
                    "name": "Programming Expert",
                    "description": "Expert programming assistant for coding, debugging, and software development",
                }
            ]
        }
    }


class AgentTypesResponse(BaseModel):
    """
    Response containing all available agent types.
    """

    agents: list[AgentTypeInfo] = Field(
        ..., description="List of available agent types"
    )
    default: AgentType = Field(..., description="Default agent type if none specified")
