from __future__ import annotations

import asyncio
import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from openai import APIError, APIConnectionError, APITimeoutError, AsyncOpenAI

from app.core.config import get_settings
from app.models.travel import LLMHealthResponse


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.llm_api_key and self.settings.llm_base_url and self.settings.llm_model)

    def _client(self) -> AsyncOpenAI:
        if not self.settings.llm_api_key or not self.settings.llm_base_url:
            raise RuntimeError("LLM_API_KEY 或 LLM_BASE_URL 未配置")
        return AsyncOpenAI(api_key=self.settings.llm_api_key, base_url=self.settings.llm_base_url, timeout=18.0)

    async def complete_json(
        self,
        system_prompt: str,
        payload: dict[str, Any],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> tuple[Any | None, str | None]:
        if not self.configured:
            return None, "LLM 未配置"

        try:
            response = await asyncio.wait_for(
                self._client().chat.completions.create(
                    model=self.settings.llm_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                system_prompt.strip()
                                + "\n\n你必须只返回合法 JSON，不要 Markdown，不要代码块，不要解释。"
                            ),
                        },
                        {
                            "role": "user",
                            "content": json.dumps(payload, ensure_ascii=False, default=_json_default),
                        },
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
                timeout=20,
            )
            content = response.choices[0].message.content if response.choices else ""
            if not content:
                return None, "LLM 返回空内容"
            return _parse_json_response(content), None
        except (asyncio.TimeoutError, APIConnectionError, APITimeoutError, APIError, ValueError, json.JSONDecodeError) as exc:
            return None, str(exc)

    async def ping(self) -> LLMHealthResponse:
        if not self.configured:
            return LLMHealthResponse(
                configured=False,
                provider=self.settings.llm_provider,
                base_url=self.settings.llm_base_url,
                model=self.settings.llm_model,
                status="not_configured",
                error="请在 backend/.env 中配置 LLM_BASE_URL、LLM_API_KEY 和 LLM_MODEL",
            )

        try:
            response = await self._client().chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {
                        "role": "user",
                        "content": "请用一句简短中文回复：AIHubMix 配置已连通。",
                    }
                ],
                temperature=0,
                max_tokens=80,
            )
            reply = response.choices[0].message.content if response.choices else ""
            if not reply:
                reply = "AIHubMix 请求成功，模型返回了空内容。"
            return LLMHealthResponse(
                configured=True,
                provider=self.settings.llm_provider,
                base_url=self.settings.llm_base_url,
                model=self.settings.llm_model,
                status="ok",
                reply=reply,
            )
        except (APIConnectionError, APITimeoutError, APIError) as exc:
            return LLMHealthResponse(
                configured=True,
                provider=self.settings.llm_provider,
                base_url=self.settings.llm_base_url,
                model=self.settings.llm_model,
                status="error",
                error=str(exc),
            )


def _json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def _parse_json_response(content: str) -> Any:
    text = content.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    candidates: list[str] = []
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise ValueError("LLM 返回内容不是合法 JSON")
