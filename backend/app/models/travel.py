from __future__ import annotations

from datetime import date as Date
from datetime import datetime as DateTime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


NonEmptyStr = Annotated[str, Field(min_length=1, max_length=160)]
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]
Rating = Annotated[float, Field(ge=0, le=5)]


class TravelBaseModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class Location(TravelBaseModel):
    city: NonEmptyStr
    district: str | None = Field(default=None, max_length=80)
    address: str | None = Field(default=None, max_length=240)
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    amap_adcode: str | None = Field(default=None, max_length=12)
    amap_poi_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def coordinates_must_be_complete(self) -> "Location":
        if (self.latitude is None) ^ (self.longitude is None):
            raise ValueError("latitude 和 longitude 必须同时提供")
        return self

    @computed_field
    @property
    def label(self) -> str:
        parts = [self.city, self.district, self.address]
        return " / ".join(part for part in parts if part)


class Attraction(TravelBaseModel):
    id: str = Field(default_factory=lambda: f"attr_{uuid4().hex[:10]}")
    name: NonEmptyStr
    location: Location
    category: str = Field(default="景点", max_length=80)
    rating: Rating | None = None
    duration_hours: Annotated[float, Field(gt=0, le=12)] = 2.0
    ticket_price: Money = Decimal("0")
    tags: list[str] = Field(default_factory=list, max_length=10)
    highlights: list[str] = Field(default_factory=list, max_length=8)
    opening_hours: str | None = Field(default=None, max_length=120)
    crowd_level: Literal["low", "medium", "high"] = "medium"
    source: str = "amap-mcp"
    map_url: str | None = None


class Hotel(TravelBaseModel):
    id: str = Field(default_factory=lambda: f"hotel_{uuid4().hex[:10]}")
    name: NonEmptyStr
    location: Location
    rating: Rating | None = None
    star_level: Annotated[int, Field(ge=0, le=5)] | None = None
    price_per_night: Money
    amenities: list[str] = Field(default_factory=list, max_length=12)
    suitable_for: list[str] = Field(default_factory=list, max_length=8)
    distance_to_center_km: Annotated[float, Field(ge=0, le=80)] | None = None
    booking_tip: str | None = Field(default=None, max_length=240)


class Meal(TravelBaseModel):
    id: str = Field(default_factory=lambda: f"meal_{uuid4().hex[:10]}")
    name: NonEmptyStr
    location: Location
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    cuisine: str = Field(default="本地菜", max_length=80)
    price_per_person: Money
    recommended_dishes: list[str] = Field(default_factory=list, max_length=8)
    rating: Rating | None = None
    reservation_required: bool = False


class WeatherDaily(TravelBaseModel):
    date: Date
    location: Location
    condition: str = Field(max_length=80)
    temperature_low: Annotated[int, Field(ge=-50, le=60)]
    temperature_high: Annotated[int, Field(ge=-50, le=60)]
    wind: str | None = Field(default=None, max_length=80)
    humidity: Annotated[int, Field(ge=0, le=100)] | None = None
    tips: list[str] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def high_must_not_be_lower_than_low(self) -> "WeatherDaily":
        if self.temperature_high < self.temperature_low:
            raise ValueError("temperature_high 不能低于 temperature_low")
        return self


class BudgetBreakdown(TravelBaseModel):
    currency: str = Field(default="CNY", min_length=3, max_length=3)
    attraction_total: Money = Decimal("0")
    hotel_total: Money = Decimal("0")
    meal_total: Money = Decimal("0")
    transport_total: Money = Decimal("0")
    buffer_total: Money = Decimal("0")

    @computed_field
    @property
    def grand_total(self) -> Decimal:
        return (
            self.attraction_total
            + self.hotel_total
            + self.meal_total
            + self.transport_total
            + self.buffer_total
        )


class DayTrip(TravelBaseModel):
    day_index: Annotated[int, Field(ge=1, le=60)]
    date: Date | None = None
    theme: NonEmptyStr
    summary: str = Field(max_length=500)
    attractions: list[Attraction] = Field(default_factory=list, max_length=8)
    meals: list[Meal] = Field(default_factory=list, max_length=5)
    hotel: Hotel | None = None
    weather: WeatherDaily | None = None
    transportation: list[str] = Field(default_factory=list, max_length=8)
    estimated_cost: Money = Decimal("0")
    notes: list[str] = Field(default_factory=list, max_length=8)
    route_points: list[Location] = Field(default_factory=list, max_length=16)


class TripPlan(TravelBaseModel):
    id: str = Field(default_factory=lambda: f"trip_{uuid4().hex[:12]}")
    destination: Location
    start_date: Date
    end_date: Date
    travelers: Annotated[int, Field(ge=1, le=20)]
    title: NonEmptyStr
    total_days: Annotated[int, Field(ge=1, le=60)]
    days: list[DayTrip] = Field(min_length=1, max_length=60)
    hotels: list[Hotel] = Field(default_factory=list, max_length=20)
    budget: BudgetBreakdown
    assumptions: list[str] = Field(default_factory=list, max_length=10)
    warnings: list[str] = Field(default_factory=list, max_length=10)
    generated_at: DateTime = Field(default_factory=DateTime.utcnow)

    @model_validator(mode="after")
    def dates_and_days_must_match(self) -> "TripPlan":
        actual_days = (self.end_date - self.start_date).days + 1
        if actual_days != self.total_days:
            raise ValueError("total_days 必须与 start_date/end_date 匹配")
        if len(self.days) != self.total_days:
            raise ValueError("days 数量必须等于 total_days")
        return self


class TravelRequest(TravelBaseModel):
    origin: Location | None = None
    destination: Location
    start_date: Date
    end_date: Date
    travelers: Annotated[int, Field(ge=1, le=20)] = 2
    budget_level: Literal["economy", "standard", "premium"] = "standard"
    interests: list[str] = Field(default_factory=lambda: ["城市地标", "美食"], max_length=12)
    pace: Literal["relaxed", "balanced", "packed"] = "balanced"
    hotel_level: Literal["budget", "comfort", "luxury"] = "comfort"
    dietary_preferences: list[str] = Field(default_factory=list, max_length=8)
    notes: str | None = Field(default=None, max_length=600)

    @field_validator("interests", "dietary_preferences")
    @classmethod
    def remove_empty_items(cls, value: list[str]) -> list[str]:
        return [item for item in dict.fromkeys(v.strip() for v in value) if item]

    @model_validator(mode="after")
    def end_date_must_not_be_before_start_date(self) -> "TravelRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date 不能早于 start_date")
        if (self.end_date - self.start_date).days > 59:
            raise ValueError("行程最多支持 60 天")
        return self


class AgentReport(TravelBaseModel):
    agent_name: str
    status: Literal["success", "partial", "failed"] = "success"
    summary: str
    started_at: DateTime
    finished_at: DateTime
    warnings: list[str] = Field(default_factory=list)


class TravelPlanResponse(TravelBaseModel):
    request_id: str = Field(default_factory=lambda: f"req_{uuid4().hex[:12]}")
    plan: TripPlan
    agents: list[AgentReport]


class HealthResponse(TravelBaseModel):
    status: Literal["ok"]
    service: str


class LLMHealthResponse(TravelBaseModel):
    configured: bool
    provider: str
    base_url: str | None = None
    model: str
    status: Literal["ok", "not_configured", "error"]
    reply: str | None = Field(default=None, max_length=500)
    error: str | None = Field(default=None, max_length=500)


class CityImageResponse(TravelBaseModel):
    city: NonEmptyStr
    configured: bool
    image_url: str | None = None
    thumb_url: str | None = None
    alt_description: str | None = Field(default=None, max_length=300)
    color: str | None = Field(default=None, max_length=24)
    photographer_name: str | None = Field(default=None, max_length=120)
    photographer_url: str | None = None
    photo_url: str | None = None
    source: Literal["unsplash", "fallback"] = "fallback"
