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
    """
    Chat endpoint with automatic memory.

    Performance: Single LLM API call per request. Memory retrieval and
    storage happen automatically via Memori in the background with zero
    added latency to the response.

    Flow:
    1. User sends a message with optional agent type
    2. Memori retrieves relevant memories for this user
    3. LLM generates response with memory context using the specified agent personality
    4. Memori extracts and stores new memories (background)
    5. Return response

    Args:
        user_id: Unique user identifier (used to isolate memories)
        request: Chat request with message, optional name, and agent type
        llm_service: LLM service with Memori integration

    Returns:
        Chat response with AI message and agent type used

    Raises:
        HTTPException: If there's an error processing the request
    """
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
