from typing import Annotated

from fastapi import APIRouter, HTTPException, Path

from app.api.deps import LLMServiceDep
from app.models.chat import ChatRequest, ChatResponse, Message

router = APIRouter()


@router.post(
    "/chat/{user_id}",
    response_model=ChatResponse,
    summary="Chat with Memory",
    description="""
    Send a message and get an AI response with memory.

    The AI will remember information from previous conversations with this user_id.
    No database setup needed - all memory is handled by Memori's hosted service!

    You can specify different agent types:
    - **general**: General purpose assistant (default)
    - **programming**: Expert programming assistant
    - **customer_support**: Professional customer support agent
    - **finance**: Personal finance advisor
    """,
)
async def chat(
    user_id: Annotated[
        str,
        Path(
            description="Unique identifier for the user (e.g., UUID)",
            examples=["550e8400-e29b-41d4-a716-446655440000"],
        ),
    ],
    request: ChatRequest,
    llm_service: LLMServiceDep,
) -> ChatResponse:
    try:
        # Get AI response with memory using specified agent type
        response_text = llm_service.chat(
            user_id=user_id,
            message=request.q,
            user_name=request.name,
            agent_type=request.agent_type,
        )

        # Build and return response
        return ChatResponse(
            messages=[Message(content=response_text, role="assistant")],
            agent_type=request.agent_type,
        )

    except Exception as e:
        # AGENTS.md: Raise meaningful exceptions with context
        raise HTTPException(
            status_code=500, detail=f"Error processing chat request: {str(e)}"
        ) from e
