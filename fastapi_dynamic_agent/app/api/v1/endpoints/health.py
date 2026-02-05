from fastapi import APIRouter

from app.api.deps import SettingsDep
from app.models.chat import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check if the service is running and get version info",
)
async def health_check(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(status="healthy", version=settings.app_version)
