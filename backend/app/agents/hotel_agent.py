from __future__ import annotations

from decimal import Decimal

from app.agents.base import TravelAgent
from app.agents.prompts import HOTEL_RECOMMENDATION_PROMPT
from app.models.travel import Hotel, Location, TravelRequest


class HotelRecommendationAgent(TravelAgent[list[Hotel]]):
    name = "酒店推荐 Agent"
    prompt = HOTEL_RECOMMENDATION_PROMPT

    async def _run(self, request: TravelRequest, warnings: list[str]) -> list[Hotel]:
        pois = await self.mcp_client.search_pois(request.destination.city, "酒店")
        if not pois:
            warnings.append("未配置或未获取到高德 MCP 酒店结果，已使用开发期示例酒店")
            return await self._fallback(request, warnings)

        price = _price_for_level(request.hotel_level)
        # Search results include coordinates through the AMap REST fallback.
        # Keeping hotel details out of the hot path prevents long stdio MCP waits.
        enriched_pois = pois[:4]

        hotels: list[Hotel] = []
        for item in enriched_pois:
            poi = item if isinstance(item, dict) else {}
            if not poi:
                continue
            hotels.append(
                Hotel(
                    name=str(poi.get("name") or "未命名酒店"),
                    location=_location_from_poi(request.destination.city, poi),
                    rating=4.4,
                    star_level={"budget": 3, "comfort": 4, "luxury": 5}[request.hotel_level],
                    price_per_night=price,
                    amenities=["近地铁", "行李寄存", "早餐"],
                    suitable_for=["情侣", "家庭", "朋友出行"],
                    booking_tip="建议选择可免费取消房型，方便根据天气调整路线。",
                )
            )
        return await self._llm_refine(request, hotels, warnings)

    async def _with_detail(self, poi: dict[str, object]) -> dict[str, object]:
        poi_id = str(poi.get("id") or "")
        detail = await self.mcp_client.get_poi_detail(poi_id)
        if not detail:
            return poi
        return {**poi, **detail}

    async def _llm_refine(
        self,
        request: TravelRequest,
        hotels: list[Hotel],
        warnings: list[str],
    ) -> list[Hotel]:
        if not self.llm_client.configured or not hotels:
            return hotels

        payload = {
            "request": request.model_dump(mode="json"),
            "candidates": [hotel.model_dump(mode="json") for hotel in hotels],
            "output_schema": {
                "ranked_names": ["只能填写 candidates 里已有的酒店 name"],
                "updates": {
                    "酒店名": {
                        "amenities": ["最多 6 个设施短语"],
                        "suitable_for": ["最多 4 个适用人群"],
                        "booking_tip": "不超过 80 字的预订建议",
                    }
                },
            },
        }
        instruction = (
            self.prompt
            + "\n请根据用户预算、人数、节奏和候选酒店做排序与轻量优化。"
            + "不能新增酒店，不能修改经纬度、地址、价格、POI ID。"
            + "返回 JSON 对象，字段只能包含 ranked_names 和 updates。"
        )
        data, error = await self.llm_client.complete_json(instruction, payload, max_tokens=900)
        if error:
            warnings.append(f"LLM 酒店优化未生效：{error}")
            return hotels
        if not isinstance(data, dict):
            warnings.append("LLM 酒店优化未生效：返回结构不是对象")
            return hotels

        ordered = _order_hotels_by_names(hotels, data.get("ranked_names"))
        updates = data.get("updates") if isinstance(data.get("updates"), dict) else {}
        refined: list[Hotel] = []
        for hotel in ordered:
            patch = updates.get(hotel.name) if isinstance(updates, dict) else None
            if not isinstance(patch, dict):
                refined.append(hotel)
                continue
            hotel_data = hotel.model_dump()
            amenities = _clean_string_list(patch.get("amenities"), 6)
            suitable_for = _clean_string_list(patch.get("suitable_for"), 4)
            booking_tip = str(patch.get("booking_tip") or "").strip()
            if amenities:
                hotel_data["amenities"] = amenities
            if suitable_for:
                hotel_data["suitable_for"] = suitable_for
            if booking_tip:
                hotel_data["booking_tip"] = booking_tip[:240]
            try:
                refined.append(Hotel.model_validate(hotel_data))
            except ValueError:
                refined.append(hotel)
        return refined or hotels

    async def _fallback(self, request: TravelRequest, warnings: list[str]) -> list[Hotel]:
        city = request.destination.city
        price = _price_for_level(request.hotel_level)
        star = {"budget": 3, "comfort": 4, "luxury": 5}[request.hotel_level]
        return [
            Hotel(
                name=f"{city}中心交通便利酒店",
                location=Location(city=city, district="核心商圈", address="地铁站周边"),
                rating=4.6,
                star_level=star,
                price_per_night=price,
                amenities=["近地铁", "早餐", "洗衣房", "行李寄存"],
                suitable_for=["首次到访", "短途旅行"],
                distance_to_center_km=1.8,
                booking_tip="优先选择靠近地铁换乘站的位置。",
            ),
            Hotel(
                name=f"{city}安静舒适型酒店",
                location=Location(city=city, district="生活街区", address="餐饮街区附近"),
                rating=4.5,
                star_level=star,
                price_per_night=(price * Decimal("0.88")).quantize(Decimal("0.01")),
                amenities=["安静房型", "早餐", "停车场"],
                suitable_for=["家庭", "慢节奏旅行"],
                distance_to_center_km=3.5,
                booking_tip="适合晚上想减少通勤和噪音的行程。",
            ),
        ]

    def _summary(self, data: list[Hotel]) -> str:
        return f"推荐 {len(data)} 个住宿候选，兼顾交通、预算和舒适度。"


def _price_for_level(level: str) -> Decimal:
    return {
        "budget": Decimal("320.00"),
        "comfort": Decimal("580.00"),
        "luxury": Decimal("1180.00"),
    }[level]


def _order_hotels_by_names(hotels: list[Hotel], ranked_names: object) -> list[Hotel]:
    if not isinstance(ranked_names, list):
        return hotels
    by_name = {hotel.name: hotel for hotel in hotels}
    ordered = [by_name[name] for name in ranked_names if isinstance(name, str) and name in by_name]
    ordered.extend(hotel for hotel in hotels if hotel.name not in {item.name for item in ordered})
    return ordered


def _clean_string_list(value: object, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in result:
            result.append(text[:80])
        if len(result) >= limit:
            break
    return result


def _location_from_poi(default_city: str, poi: dict[str, object]) -> Location:
    lon: float | None = None
    lat: float | None = None
    raw_location = poi.get("location")
    if isinstance(raw_location, str) and "," in raw_location:
        raw_lon, raw_lat = raw_location.split(",", 1)
        try:
            lon = float(raw_lon)
            lat = float(raw_lat)
        except ValueError:
            lon = None
            lat = None

    return Location(
        city=str(poi.get("cityname") or poi.get("city") or default_city),
        district=str(poi.get("adname") or "") or None,
        address=str(poi.get("address") or "") or None,
        latitude=lat,
        longitude=lon,
        amap_adcode=str(poi.get("adcode") or "") or None,
        amap_poi_id=str(poi.get("id") or "") or None,
    )
