from fastapi import APIRouter

from app.api.v1.endpoints import agents, chat, health

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])

api_router.include_router(chat.router, prefix="/api/v1", tags=["chat"])

api_router.include_router(agents.router, prefix="/api/v1", tags=["agents"])
