from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.agents.amap_mcp import AmapMCPClient
from app.models.travel import AgentReport, TravelRequest
from app.services.llm import LLMClient


T = TypeVar("T")


class AgentOutput(BaseModel, Generic[T]):
    data: T
    report: AgentReport


class AgentRunContext(BaseModel):
    request: TravelRequest
    started_at: datetime = Field(default_factory=datetime.utcnow)


class TravelAgent(ABC, Generic[T]):
    name: str
    prompt: str

    def __init__(self, mcp_client: AmapMCPClient | None = None, llm_client: LLMClient | None = None) -> None:
        self.mcp_client = mcp_client or AmapMCPClient()
        self.llm_client = llm_client or LLMClient()

    async def run(self, request: TravelRequest) -> AgentOutput[T]:
        started_at = datetime.utcnow()
        warnings: list[str] = []
        status = "success"
        try:
            data = await self._run(request, warnings)
        except Exception as exc:  # MCP failures should not break local planning.
            status = "partial"
            warnings.append(f"{self.name} 使用备用数据：{exc}")
            data = await self._fallback(request, warnings)

        finished_at = datetime.utcnow()
        return AgentOutput(
            data=data,
            report=AgentReport(
                agent_name=self.name,
                status=status,
                summary=self._summary(data),
                started_at=started_at,
                finished_at=finished_at,
                warnings=warnings,
            ),
        )

    @abstractmethod
    async def _run(self, request: TravelRequest, warnings: list[str]) -> T:
        raise NotImplementedError

    @abstractmethod
    async def _fallback(self, request: TravelRequest, warnings: list[str]) -> T:
        raise NotImplementedError

    @abstractmethod
    def _summary(self, data: T) -> str:
        raise NotImplementedError
