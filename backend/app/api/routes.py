import httpx
from fastapi import APIRouter, HTTPException, Query

from app.agents.orchestrator import TravelPlannerOrchestrator
from app.models.travel import (
    CityImageResponse,
    HealthResponse,
    LLMHealthResponse,
    TravelPlanResponse,
    TravelRequest,
)
from app.services.llm import LLMClient
from app.services.unsplash import UnsplashClient


router = APIRouter()
orchestrator = TravelPlannerOrchestrator()
unsplash_client = UnsplashClient()
llm_client = LLMClient()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="travel-agent-backend")


@router.get("/llm/health", response_model=LLMHealthResponse)
async def llm_health() -> LLMHealthResponse:
    return await llm_client.ping()


@router.post("/trips/plan", response_model=TravelPlanResponse)
async def create_trip_plan(payload: TravelRequest) -> TravelPlanResponse:
    return await orchestrator.build_plan(payload)


@router.get("/media/city-image", response_model=CityImageResponse)
async def get_city_image(city: str = Query(..., min_length=1, max_length=80)) -> CityImageResponse:
    try:
        return await unsplash_client.city_image(city)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail="Unsplash API 请求失败") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="无法连接 Unsplash API") from exc
