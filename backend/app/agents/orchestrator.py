from __future__ import annotations

import asyncio
from datetime import datetime

from app.agents.amap_mcp import AmapMCPClient
from app.agents.attraction_agent import AttractionSearchAgent
from app.agents.hotel_agent import HotelRecommendationAgent
from app.agents.planning_agent import PlanningAgent
from app.agents.weather_agent import WeatherQueryAgent
from app.models.travel import AgentReport, TravelPlanResponse, TravelRequest
from app.services.llm import LLMClient


class TravelPlannerOrchestrator:
    def __init__(self) -> None:
        mcp_client = AmapMCPClient()
        llm_client = LLMClient()
        self.attraction_agent = AttractionSearchAgent(mcp_client, llm_client)
        self.weather_agent = WeatherQueryAgent(mcp_client, llm_client)
        self.hotel_agent = HotelRecommendationAgent(mcp_client, llm_client)
        self.planning_agent = PlanningAgent(llm_client)

    async def build_plan(self, request: TravelRequest) -> TravelPlanResponse:
        attraction_task = self.attraction_agent.run(request)
        weather_task = self.weather_agent.run(request)
        hotel_task = self.hotel_agent.run(request)

        attraction_output, weather_output, hotel_output = await asyncio.gather(
            attraction_task,
            weather_task,
            hotel_task,
        )

        planning_started = datetime.utcnow()
        plan, planning_summary = await self.planning_agent.run(
            request=request,
            attractions=attraction_output.data,
            weather=weather_output.data,
            hotels=hotel_output.data,
        )
        planning_report = AgentReport(
            agent_name=self.planning_agent.name,
            status="success",
            summary=planning_summary,
            started_at=planning_started,
            finished_at=datetime.utcnow(),
        )

        return TravelPlanResponse(
            plan=plan,
            agents=[
                attraction_output.report,
                weather_output.report,
                hotel_output.report,
                planning_report,
            ],
        )
