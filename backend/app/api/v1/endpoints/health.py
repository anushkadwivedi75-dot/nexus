from fastapi import APIRouter, status
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Confirms that the API service is running and healthy without authentication.",
)
async def check_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="nexus-api",
        version="0.1.0",
        environment=settings.APP_ENV,
    )

