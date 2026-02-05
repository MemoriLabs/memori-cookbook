from enum import Enum

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    GENERAL = "general"
    PROGRAMMING = "programming"
    CUSTOMER_SUPPORT = "customer_support"
    FINANCE = "finance"


class AgentTypeInfo(BaseModel):
    type: AgentType = Field(..., description="Agent type identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="What this agent specializes in")


class AgentTypesResponse(BaseModel):
    agents: list[AgentTypeInfo] = Field(
        ..., description="List of available agent types"
    )
    default: AgentType = Field(..., description="Default agent type if none specified")
