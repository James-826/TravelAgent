from __future__ import annotations

from datetime import date, timedelta

from app.agents.base import TravelAgent
from app.agents.prompts import WEATHER_QUERY_PROMPT
from app.models.travel import Location, TravelRequest, WeatherDaily


class WeatherQueryAgent(TravelAgent[list[WeatherDaily]]):
    name = "天气查询 Agent"
    prompt = WEATHER_QUERY_PROMPT

    async def _run(self, request: TravelRequest, warnings: list[str]) -> list[WeatherDaily]:
        result = await self.mcp_client.get_weather(request.destination.city)
        if not result:
            warnings.append("未配置或未获取到高德 MCP 天气结果，已使用季节性示例天气")
            weather = await self._fallback(request, warnings)
            return await self._llm_refine(request, weather, warnings)
        weather = _weather_from_mcp_result(request, result) or await self._fallback(request, warnings)
        return await self._llm_refine(request, weather, warnings)

    async def _llm_refine(
        self,
        request: TravelRequest,
        weather: list[WeatherDaily],
        warnings: list[str],
    ) -> list[WeatherDaily]:
        if not self.llm_client.configured or not weather:
            return weather

        payload = {
            "request": request.model_dump(mode="json"),
            "weather": [item.model_dump(mode="json") for item in weather],
            "output_schema": {
                "tips_by_date": {
                    "YYYY-MM-DD": ["最多 4 条旅行天气建议，必须基于已有天气事实"]
                }
            },
        }
        instruction = (
            self.prompt
            + "\n请只根据已有 weather 数据生成更适合旅行安排的每日 tips。"
            + "不能修改日期、天气、温度、湿度和风力，不能编造灾害预警。"
            + "返回 JSON 对象，字段只能包含 tips_by_date。"
        )
        data, error = await self.llm_client.complete_json(instruction, payload, max_tokens=700)
        if error:
            warnings.append(f"LLM 天气建议未生效：{error}")
            return weather
        if not isinstance(data, dict):
            warnings.append("LLM 天气建议未生效：返回结构不是对象")
            return weather

        tips_by_date = data.get("tips_by_date")
        if not isinstance(tips_by_date, dict):
            return weather

        refined: list[WeatherDaily] = []
        for item in weather:
            item_data = item.model_dump()
            tips = _clean_string_list(tips_by_date.get(item.date.isoformat()), 4)
            if tips:
                item_data["tips"] = tips
            try:
                refined.append(WeatherDaily.model_validate(item_data))
            except ValueError:
                refined.append(item)
        return refined or weather

    async def _fallback(self, request: TravelRequest, warnings: list[str]) -> list[WeatherDaily]:
        days = (request.end_date - request.start_date).days + 1
        output: list[WeatherDaily] = []
        for offset in range(days):
            current = request.start_date + timedelta(days=offset)
            output.append(
                WeatherDaily(
                    date=current,
                    location=request.destination,
                    condition="多云",
                    temperature_low=18 + (offset % 3),
                    temperature_high=26 + (offset % 4),
                    wind="微风",
                    humidity=62,
                    tips=["适合步行游览", "准备轻便外套和雨具"],
                )
            )
        return output

    def _summary(self, data: list[WeatherDaily]) -> str:
        return f"整理 {len(data)} 天天气与出行提示。"


def _weather_from_mcp_result(request: TravelRequest, result: dict[str, object]) -> list[WeatherDaily]:
    forecasts = result.get("forecasts") if isinstance(result, dict) else None
    if not isinstance(forecasts, list) or not forecasts:
        return []

    if forecasts and isinstance(forecasts[0], dict) and "casts" in forecasts[0]:
        casts = forecasts[0].get("casts")
    else:
        casts = forecasts
    if not isinstance(casts, list):
        return []

    output: list[WeatherDaily] = []
    for cast in casts:
        if not isinstance(cast, dict):
            continue
        raw_date = cast.get("date")
        try:
            forecast_date = date.fromisoformat(str(raw_date))
        except ValueError:
            continue
        if not (request.start_date <= forecast_date <= request.end_date):
            continue
        output.append(
            WeatherDaily(
                date=forecast_date,
                location=Location(city=request.destination.city),
                condition=str(cast.get("dayweather") or cast.get("nightweather") or "未知"),
                temperature_low=int(cast.get("nighttemp") or 0),
                temperature_high=int(cast.get("daytemp") or 0),
                wind=str(cast.get("daywind") or "") or None,
                tips=_tips_for_weather(str(cast.get("dayweather") or "")),
            )
        )
    return output


def _tips_for_weather(condition: str) -> list[str]:
    if "雨" in condition:
        return ["优先安排室内景点", "携带雨具并预留打车预算"]
    if "晴" in condition:
        return ["注意防晒", "户外景点可安排在上午或傍晚"]
    return ["关注实时天气", "保留一处可替换的室内项目"]


def _clean_string_list(value: object, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in result:
            result.append(text[:100])
        if len(result) >= limit:
            break
    return result
