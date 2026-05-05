from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Iterable

from app.agents.base import TravelAgent
from app.agents.prompts import ATTRACTION_SEARCH_PROMPT
from app.models.travel import Attraction, Location, TravelRequest


class AttractionSearchAgent(TravelAgent[list[Attraction]]):
    name = "景点搜索 Agent"
    prompt = ATTRACTION_SEARCH_PROMPT

    async def _run(self, request: TravelRequest, warnings: list[str]) -> list[Attraction]:
        keywords = _search_keywords(request)
        poi_batches = await asyncio.gather(
            *(self.mcp_client.search_pois(request.destination.city, keyword) for keyword in keywords),
            return_exceptions=True,
        )
        pois = _interleave_poi_batches(batch for batch in poi_batches if isinstance(batch, list))
        if not pois:
            warnings.append("未配置或未获取到高德 MCP 景点结果，已使用开发期示例景点")
            return await self._fallback(request, warnings)

        # Text search already falls back to AMap REST when MCP misses coordinates.
        # Avoid detail calls for every POI because stdio MCP starts an npx process per call.
        enriched_pois = pois[:12]

        attractions: list[Attraction] = []
        for item in enriched_pois:
            poi = item if isinstance(item, dict) else {}
            if not poi or not _is_good_attraction(poi):
                continue
            location = _location_from_poi(request.destination.city, poi)
            attractions.append(
                Attraction(
                    name=str(poi.get("name") or "未命名景点"),
                    location=location,
                    category=_category_from_poi(poi),
                    rating=_safe_rating(poi.get("rating") or _nested_biz_value(poi, "rating")),
                    duration_hours=_duration_for_poi(poi),
                    ticket_price=_ticket_price_from_poi(poi),
                    tags=_tags_for_poi(poi, request.interests),
                    highlights=_highlights_for_poi(poi),
                    opening_hours=str(poi.get("opentime") or "") or None,
                    crowd_level=_crowd_level_for_poi(poi),
                )
            )
        attractions = _dedupe_attractions(attractions)
        if not attractions:
            warnings.append("高德返回结果不适合做景点，已使用开发期示例景点")
            return await self._fallback(request, warnings)
        return await self._llm_refine(request, attractions[:12], warnings)

    async def _with_detail(self, poi: dict[str, object]) -> dict[str, object]:
        poi_id = str(poi.get("id") or "")
        detail = await self.mcp_client.get_poi_detail(poi_id)
        if not detail:
            return poi
        return {**poi, **detail}

    async def _llm_refine(
        self,
        request: TravelRequest,
        attractions: list[Attraction],
        warnings: list[str],
    ) -> list[Attraction]:
        if not self.llm_client.configured or not attractions:
            return attractions

        payload = {
            "request": request.model_dump(mode="json"),
            "candidates": [attraction.model_dump(mode="json") for attraction in attractions],
            "output_schema": {
                "selected_names": ["只能填写 candidates 里已有的景点 name"],
                "updates": {
                    "景点名": {
                        "tags": ["最多 5 个标签"],
                        "highlights": ["最多 3 条亮点"],
                        "crowd_level": "low | medium | high",
                    }
                },
            },
        }
        instruction = (
            self.prompt
            + "\n请根据用户兴趣和旅行节奏，从候选景点中排序并轻量优化标签和亮点。"
            + "不能新增候选外景点，不能修改经纬度、地址、POI ID、门票和游玩时长。"
            + "返回 JSON 对象，字段只能包含 selected_names 和 updates。"
        )
        data, error = await self.llm_client.complete_json(instruction, payload, max_tokens=1200)
        if error:
            warnings.append(f"LLM 景点优化未生效：{error}")
            return attractions
        if not isinstance(data, dict):
            warnings.append("LLM 景点优化未生效：返回结构不是对象")
            return attractions

        ordered = _order_attractions_by_names(attractions, data.get("selected_names"))
        updates = data.get("updates") if isinstance(data.get("updates"), dict) else {}
        refined: list[Attraction] = []
        for attraction in ordered:
            patch = updates.get(attraction.name) if isinstance(updates, dict) else None
            if not isinstance(patch, dict):
                refined.append(attraction)
                continue
            attraction_data = attraction.model_dump()
            tags = _clean_string_list(patch.get("tags"), 5)
            highlights = _clean_string_list(patch.get("highlights"), 3)
            crowd_level = str(patch.get("crowd_level") or "").strip()
            if tags:
                attraction_data["tags"] = tags
            if highlights:
                attraction_data["highlights"] = highlights
            if crowd_level in {"low", "medium", "high"}:
                attraction_data["crowd_level"] = crowd_level
            try:
                refined.append(Attraction.model_validate(attraction_data))
            except ValueError:
                refined.append(attraction)
        return refined[:12] or attractions

    async def _fallback(self, request: TravelRequest, warnings: list[str]) -> list[Attraction]:
        city = request.destination.city
        tags = request.interests[:3] or ["城市地标"]
        return [
            Attraction(
                name=f"{city}城市地标步行区",
                location=Location(city=city, district="核心区", address="市中心片区"),
                category="城市地标",
                rating=4.6,
                duration_hours=2.5,
                ticket_price=Decimal("0.00"),
                tags=tags,
                highlights=["适合抵达后熟悉城市", "拍照与街区漫步体验稳定"],
                opening_hours="全天开放",
                crowd_level="medium",
                source="fallback",
            ),
            Attraction(
                name=f"{city}历史文化街区",
                location=Location(city=city, district="老城片区", address="历史街区"),
                category="人文历史",
                rating=4.5,
                duration_hours=3.0,
                ticket_price=Decimal("40.00"),
                tags=["文化", *tags[:2]],
                highlights=["地方文化集中", "适合安排讲解或慢游"],
                opening_hours="09:00-18:00",
                crowd_level="high",
                source="fallback",
            ),
            Attraction(
                name=f"{city}城市公园与观景点",
                location=Location(city=city, district="生态片区", address="城市公园"),
                category="自然休闲",
                rating=4.4,
                duration_hours=2.0,
                ticket_price=Decimal("20.00"),
                tags=["自然", "亲子", *tags[:1]],
                highlights=["节奏轻松", "适合天气良好时安排"],
                opening_hours="08:00-21:00",
                crowd_level="low",
                source="fallback",
            ),
        ]

    def _summary(self, data: list[Attraction]) -> str:
        return f"筛选 {len(data)} 个候选景点，包含地标、人文与休闲类型。"


def _safe_rating(value: object) -> float | None:
    try:
        if value in (None, "", []):
            return None
        return max(0.0, min(5.0, float(value)))
    except (TypeError, ValueError):
        return None


def _order_attractions_by_names(attractions: list[Attraction], selected_names: object) -> list[Attraction]:
    if not isinstance(selected_names, list):
        return attractions
    by_name = {attraction.name: attraction for attraction in attractions}
    ordered = [by_name[name] for name in selected_names if isinstance(name, str) and name in by_name]
    ordered.extend(attraction for attraction in attractions if attraction.name not in {item.name for item in ordered})
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


def _search_keywords(request: TravelRequest) -> list[str]:
    base = []
    for item in request.interests:
        keyword = item.strip()
        if not keyword:
            continue
        if "美食" in keyword and "街" not in keyword:
            base.append("美食街")
            base.append("步行街")
            continue
        base.append(keyword)
    defaults = ["热门景点", "风景名胜", "博物馆", "历史文化"]
    keywords: list[str] = []
    for item in [*base, *defaults]:
        keyword = item.strip()
        if keyword and keyword not in keywords:
            keywords.append(keyword)
    return keywords[:4]


def _interleave_poi_batches(batches: Iterable[list[dict[str, object]]]) -> list[dict[str, object]]:
    rows = [batch[:8] for batch in batches if batch]
    seen: set[str] = set()
    merged: list[dict[str, object]] = []
    for index in range(max((len(row) for row in rows), default=0)):
        for row in rows:
            if index >= len(row):
                continue
            poi = row[index]
            key = str(poi.get("id") or poi.get("name") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(poi)
    return merged


def _is_good_attraction(poi: dict[str, object]) -> bool:
    name = str(poi.get("name") or "").strip()
    type_text = str(poi.get("type") or poi.get("typecode") or "")
    address = str(poi.get("address") or "")
    text = f"{name} {type_text} {address}"
    if len(name) <= 1 or name in {"地标", "景点", "热门景点"}:
        return False
    bad_words = [
        "酒店",
        "宾馆",
        "停车场",
        "停车",
        "住宅",
        "小区",
        "公司",
        "写字楼",
        "售楼",
        "健身",
        "培训",
        "学校",
        "银行",
        "诊所",
        "药房",
        "厕所",
        "加油站",
        "公交",
        "地铁站",
        "餐厅",
        "餐馆",
        "饭店",
        "小吃店",
        "购物中心",
        "商场",
        "综合大楼店",
        "店)",
    ]
    if any(word in text for word in bad_words):
        return False
    good_words = [
        "风景",
        "名胜",
        "景区",
        "景点",
        "公园",
        "博物馆",
        "纪念馆",
        "美术馆",
        "文化",
        "历史",
        "街区",
        "古镇",
        "寺",
        "塔",
        "湖",
        "山",
        "园",
        "故居",
        "遗址",
        "展览",
        "旅游",
        "美食街",
        "步行街",
        "夜市",
    ]
    return any(word in text for word in good_words)


def _category_from_poi(poi: dict[str, object]) -> str:
    type_text = str(poi.get("type") or "")
    name = str(poi.get("name") or "")
    text = f"{type_text} {name}"
    if any(word in text for word in ["美食街", "步行街", "夜市", "街区"]):
        return "特色街区"
    if any(word in text for word in ["博物馆", "纪念馆", "美术馆", "展览"]):
        return "博物馆与展览"
    if any(word in text for word in ["历史", "文化", "故居", "遗址", "古镇", "寺", "塔"]):
        return "历史文化"
    if any(word in text for word in ["风景", "名胜", "景区", "公园", "湖", "山"]):
        return "自然景观"
    return "城市探索"


def _duration_for_poi(poi: dict[str, object]) -> float:
    category = _category_from_poi(poi)
    if category == "博物馆与展览":
        return 2.0
    if category == "自然景观":
        return 3.0
    if category == "历史文化":
        return 2.5
    return 1.5


def _ticket_price_from_poi(poi: dict[str, object]) -> Decimal:
    raw_price = poi.get("cost") or poi.get("price") or _nested_biz_value(poi, "cost")
    price = _safe_money(raw_price)
    if price is not None:
        return price
    category = _category_from_poi(poi)
    name = str(poi.get("name") or "")
    if category in {"博物馆与展览", "特色街区"} or any(word in name for word in ["公园", "湖滨", "街区"]):
        return Decimal("0.00")
    if category == "自然景观":
        return Decimal("40.00")
    return Decimal("30.00")


def _safe_money(value: object) -> Decimal | None:
    if value in (None, "", [], "[]"):
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception:
        return None


def _nested_biz_value(poi: dict[str, object], key: str) -> object | None:
    biz_ext = poi.get("biz_ext")
    if isinstance(biz_ext, dict):
        return biz_ext.get(key)
    return None


def _tags_for_poi(poi: dict[str, object], interests: list[str]) -> list[str]:
    tags = [_category_from_poi(poi), *interests[:3]]
    return list(dict.fromkeys(tag for tag in tags if tag))[:5]


def _highlights_for_poi(poi: dict[str, object]) -> list[str]:
    category = _category_from_poi(poi)
    if category == "自然景观":
        return ["适合安排在天气较好的时段", "游览时间建议预留充足"]
    if category == "博物馆与展览":
        return ["适合雨天或午后安排", "建议提前确认开放时间"]
    if category == "历史文化":
        return ["适合搭配讲解或慢游", "与周边街区可组合成半日路线"]
    return ["适合补充城市体验", "可根据体力灵活调整"]


def _crowd_level_for_poi(poi: dict[str, object]) -> str:
    name = str(poi.get("name") or "")
    if any(word in name for word in ["西湖", "灵隐", "热门", "风景名胜"]):
        return "high"
    return "medium"


def _dedupe_attractions(attractions: list[Attraction]) -> list[Attraction]:
    seen: set[str] = set()
    result: list[Attraction] = []
    for attraction in attractions:
        key = attraction.location.amap_poi_id or attraction.name
        if key in seen:
            continue
        seen.add(key)
        result.append(attraction)
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
