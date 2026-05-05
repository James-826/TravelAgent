from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from math import inf

from app.agents.prompts import PLANNING_PROMPT
from app.models.travel import Attraction, DayTrip, Hotel, Location, Meal, TripPlan, TravelRequest, WeatherDaily
from app.services.budget import calculate_budget
from app.services.llm import LLMClient


class PlanningAgent:
    name = "计划规划 Agent"
    prompt = PLANNING_PROMPT

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    async def run(
        self,
        request: TravelRequest,
        attractions: list[Attraction],
        weather: list[WeatherDaily],
        hotels: list[Hotel],
    ) -> tuple[TripPlan, str]:
        total_days = (request.end_date - request.start_date).days + 1
        total_nights = max(total_days - 1, 0)
        selected_hotel = hotels[0] if hotels else None
        days: list[DayTrip] = []
        day_groups = _group_attractions_by_day(attractions, total_days, request.pace, selected_hotel)

        for index in range(total_days):
            current_date = request.start_date + timedelta(days=index)
            day_weather = next((item for item in weather if item.date == current_date), None)
            day_attractions = day_groups[index] if index < len(day_groups) else []
            meals = _default_meals(request.destination, request.travelers, request.dietary_preferences)
            route_points = _ordered_route_points(selected_hotel, day_attractions)
            hotel_for_cost = selected_hotel if selected_hotel and index < total_nights else None

            estimated_cost = _estimate_day_cost(day_attractions, meals, hotel_for_cost, request.travelers)
            days.append(
                DayTrip(
                    day_index=index + 1,
                    date=current_date,
                    theme=_theme_for_day(index, day_attractions),
                    summary=_summary_for_day(current_date, day_attractions, day_weather),
                    attractions=day_attractions,
                    meals=meals,
                    hotel=selected_hotel,
                    weather=day_weather,
                    transportation=_transport_for_route(day_attractions, request.pace),
                    estimated_cost=estimated_cost,
                    notes=_notes_for_day(day_weather),
                    route_points=route_points,
                )
            )

        budget_hotels = [selected_hotel] * total_nights if selected_hotel else []
        budget = calculate_budget(days, budget_hotels, request.travelers)
        warnings = []
        if len(attractions) < total_days:
            warnings.append("景点候选数量偏少，部分日期会保留弹性探索时间。")
        plan = TripPlan(
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            travelers=request.travelers,
            title=f"{request.destination.city}{total_days}天智能旅行计划",
            total_days=total_days,
            days=days,
            hotels=hotels,
            budget=budget,
            assumptions=[
                "门票、餐饮和交通为规划预算估算，真实价格以官方渠道和现场为准。",
                "住宿预算按晚数计算，退房当天不重复计算房费。",
            ],
            warnings=warnings,
        )
        plan, llm_note = await self._llm_polish_plan(request, plan)
        summary = f"生成 {total_days} 天行程，预算约 {plan.budget.grand_total} {plan.budget.currency}{llm_note}。"
        return plan, summary

    async def _llm_polish_plan(self, request: TravelRequest, plan: TripPlan) -> tuple[TripPlan, str]:
        if not self.llm_client.configured:
            return plan, ""

        payload = {
            "request": request.model_dump(mode="json"),
            "plan": plan.model_dump(mode="json"),
            "output_schema": {
                "title": "可选，新的行程标题",
                "days": [
                    {
                        "day_index": 1,
                        "theme": "可选，每日主题",
                        "summary": "可选，每日摘要",
                        "transportation": ["可选，最多 4 条交通建议"],
                        "notes": ["可选，最多 4 条注意事项"],
                    }
                ],
                "assumptions": ["可选，最多 4 条"],
                "warnings": ["可选，最多 4 条"],
            },
        }
        instruction = (
            self.prompt
            + "\n请在不改变景点、酒店、天气、预算、日期和 route_points 的前提下，优化行程表达。"
            + "只能返回 title、days、assumptions、warnings 这些文字补丁。"
            + "days 内必须用 day_index 指定要修改哪一天。"
        )
        data, error = await self.llm_client.complete_json(instruction, payload, max_tokens=1500)
        if error:
            plan.warnings = [*plan.warnings, f"LLM 规划优化未生效：{error}"][:10]
            return plan, ""
        if not isinstance(data, dict):
            plan.warnings = [*plan.warnings, "LLM 规划优化未生效：返回结构不是对象"][:10]
            return plan, ""

        title = str(data.get("title") or "").strip()
        if title:
            plan.title = title[:160]

        day_patches = data.get("days")
        if isinstance(day_patches, list):
            by_index = {day.day_index: day for day in plan.days}
            for patch in day_patches:
                if not isinstance(patch, dict):
                    continue
                try:
                    day = by_index.get(int(patch.get("day_index")))
                except (TypeError, ValueError):
                    day = None
                if not day:
                    continue
                theme = str(patch.get("theme") or "").strip()
                summary = str(patch.get("summary") or "").strip()
                transportation = _clean_string_list(patch.get("transportation"), 4, 120)
                notes = _clean_string_list(patch.get("notes"), 4, 120)
                if theme:
                    day.theme = theme[:160]
                if summary:
                    day.summary = summary[:500]
                if transportation:
                    day.transportation = transportation
                if notes:
                    day.notes = notes

        assumptions = _clean_string_list(data.get("assumptions"), 4, 160)
        warnings = _clean_string_list(data.get("warnings"), 4, 160)
        if assumptions:
            plan.assumptions = [*plan.assumptions, *assumptions][:10]
        if warnings:
            plan.warnings = [*plan.warnings, *warnings][:10]
        return plan, "，已用 LLM 优化行程说明"


def _group_attractions_by_day(
    attractions: list[Attraction],
    total_days: int,
    pace: str,
    hotel: Hotel | None,
) -> list[list[Attraction]]:
    if not attractions:
        return [[] for _ in range(total_days)]

    per_day = {"relaxed": 2, "balanced": 2, "packed": 3}[pace]
    candidates = _dedupe_attractions(attractions)[: total_days * per_day]
    candidates = _sort_spatially(candidates, hotel.location if hotel else None)
    groups: list[list[Attraction]] = [[] for _ in range(total_days)]
    for index, attraction in enumerate(candidates):
        groups[index // per_day].append(attraction)
        if index // per_day >= total_days - 1:
            break
    return groups


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


def _sort_spatially(attractions: list[Attraction], start: Location | None) -> list[Attraction]:
    with_coordinates = [item for item in attractions if _has_coordinates(item.location)]
    without_coordinates = [item for item in attractions if not _has_coordinates(item.location)]
    if not with_coordinates:
        return attractions

    ordered: list[Attraction] = []
    remaining = with_coordinates[:]
    current = start if start and _has_coordinates(start) else remaining[0].location
    while remaining:
        next_item = min(remaining, key=lambda item: _distance(current, item.location))
        ordered.append(next_item)
        remaining.remove(next_item)
        current = next_item.location
    return [*ordered, *without_coordinates]


def _ordered_route_points(hotel: Hotel | None, attractions: list[Attraction]) -> list[Location]:
    points: list[Location] = []
    if hotel:
        points.append(hotel.location)
    points.extend(item.location for item in attractions)
    return _dedupe_locations(points)


def _dedupe_locations(locations: list[Location]) -> list[Location]:
    seen: set[str] = set()
    result: list[Location] = []
    for location in locations:
        key = (
            f"{location.longitude:.6f},{location.latitude:.6f}"
            if location.latitude is not None and location.longitude is not None
            else location.label
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(location)
    return result


def _has_coordinates(location: Location) -> bool:
    return location.latitude is not None and location.longitude is not None


def _distance(a: Location, b: Location) -> float:
    if not _has_coordinates(a) or not _has_coordinates(b):
        return inf
    return (a.latitude - b.latitude) ** 2 + (a.longitude - b.longitude) ** 2


def _default_meals(destination: Location, travelers: int, dietary_preferences: list[str]) -> list[Meal]:
    preference = "、".join(dietary_preferences) if dietary_preferences else "本地风味"
    return [
        Meal(
            name=f"{destination.city}街区早餐",
            location=Location(city=destination.city, district=destination.district, address="酒店周边"),
            meal_type="breakfast",
            cuisine=preference,
            price_per_person=Decimal("35.00"),
            recommended_dishes=["本地早餐", "热饮"],
        ),
        Meal(
            name=f"{destination.city}特色午餐",
            location=Location(city=destination.city, district=destination.district, address="景点周边"),
            meal_type="lunch",
            cuisine=preference,
            price_per_person=Decimal("85.00"),
            recommended_dishes=["招牌菜", "时令小吃"],
            reservation_required=travelers >= 5,
        ),
        Meal(
            name=f"{destination.city}轻松晚餐",
            location=Location(city=destination.city, district=destination.district, address="住宿周边"),
            meal_type="dinner",
            cuisine=preference,
            price_per_person=Decimal("120.00"),
            recommended_dishes=["地方菜", "甜品"],
            reservation_required=True,
        ),
    ]


def _theme_for_day(index: int, attractions: list[Attraction]) -> str:
    if not attractions:
        return f"第 {index + 1} 天弹性探索"
    categories = list(dict.fromkeys(item.category for item in attractions))
    main_name = attractions[0].name
    if len(categories) == 1:
        return f"第 {index + 1} 天：{main_name}周边深度游"
    return f"第 {index + 1} 天：{categories[0]} + {categories[1]}"


def _summary_for_day(current_date, attractions: list[Attraction], weather: WeatherDaily | None) -> str:
    names = "、".join(item.name for item in attractions) or "轻量城市探索"
    weather_text = f"，天气预计{weather.condition}" if weather else ""
    return f"{current_date:%Y-%m-%d} 安排 {names}{weather_text}。路线按相邻点位组织，避免跨城来回折返。"


def _transport_for_route(attractions: list[Attraction], pace: str) -> list[str]:
    names = "、".join(item.name for item in attractions[:3]) or "目的地周边"
    if pace == "relaxed":
        return [f"酒店出发后前往 {names}", "景点之间优先选择步行或短途打车", "晚餐后直接返回酒店"]
    if pace == "packed":
        return [f"使用地铁和打车组合串联 {names}", "午餐选择景点附近", "晚间可追加同区域夜景点"]
    return [f"上午前往 {names}", "下午沿相邻点位顺路游览", "晚餐后根据体力决定是否加点"]


def _estimate_day_cost(
    attractions: list[Attraction],
    meals: list[Meal],
    hotel: Hotel | None,
    travelers: int,
) -> Decimal:
    attraction_cost = sum((item.ticket_price for item in attractions), start=Decimal("0")) * travelers
    meal_cost = sum((item.price_per_person for item in meals), start=Decimal("0")) * travelers
    hotel_cost = hotel.price_per_night if hotel else Decimal("0")
    transport_cost = Decimal("80.00") * travelers
    return (attraction_cost + meal_cost + hotel_cost + transport_cost).quantize(Decimal("0.01"))


def _notes_for_day(weather: WeatherDaily | None) -> list[str]:
    notes = ["建议提前确认景点开放时间", "随身携带身份证件和充电宝"]
    if weather:
        notes.extend(weather.tips[:2])
    return notes


def _clean_string_list(value: object, limit: int, item_max_length: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in result:
            result.append(text[:item_max_length])
        if len(result) >= limit:
            break
    return result
