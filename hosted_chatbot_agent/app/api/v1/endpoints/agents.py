from fastapi import APIRouter

from app.models.agents import AgentType, AgentTypeInfo, AgentTypesResponse

router = APIRouter()


# Agent metadata - descriptions for each type
AGENT_METADATA = {
    AgentType.GENERAL: {
        "name": "General Assistant",
        "description": "Knowledgeable, friendly assistant for a wide range of topics and questions",
    },
    AgentType.PROGRAMMING: {
        "name": "Programming Expert",
        "description": "Expert programming assistant for coding, debugging, best practices, and software development",
    },
    AgentType.CUSTOMER_SUPPORT: {
        "name": "Customer Support",
        "description": "Professional, empathetic support agent focused on resolving issues efficiently",
    },
    AgentType.FINANCE: {
        "name": "Personal Finance Advisor",
        "description": "Financial planning and advice expert for budgeting, investing, and money management",
    },
}


@router.get(
    "/agents",
    response_model=AgentTypesResponse,
    summary="Get Available Agent Types",
    description="""
    Returns a list of all available agent types that can be used in chat conversations.

    Each agent has a specialized personality and knowledge base. Use the `agent_type` field
    when making chat requests to specify which agent to use.

    The response includes a `default` field indicating which agent is used when none is specified.
    """,
)
async def get_agent_types() -> AgentTypesResponse:
    agents = [
        AgentTypeInfo(
            type=agent_type, name=metadata["name"], description=metadata["description"]
        )
        for agent_type, metadata in AGENT_METADATA.items()
    ]

    return AgentTypesResponse(agents=agents, default=AgentType.GENERAL)
