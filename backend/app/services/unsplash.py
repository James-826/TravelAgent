from __future__ import annotations

from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import httpx

from app.core.config import get_settings
from app.models.travel import CityImageResponse


UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"


class UnsplashClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def city_image(self, city: str) -> CityImageResponse:
        if not self.settings.unsplash_access_key:
            return CityImageResponse(
                city=city,
                configured=False,
                alt_description="配置 UNSPLASH_ACCESS_KEY 后显示城市图片",
            )

        params = {
            "query": f"{city} city travel skyline",
            "per_page": 1,
            "orientation": "landscape",
            "content_filter": "high",
        }
        headers = {
            "Authorization": f"Client-ID {self.settings.unsplash_access_key}",
            "Accept-Version": "v1",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(UNSPLASH_SEARCH_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        if not results:
            return CityImageResponse(
                city=city,
                configured=True,
                alt_description=f"没有找到 {city} 的城市图片",
            )

        photo = results[0]
        user = photo.get("user", {}) if isinstance(photo.get("user"), dict) else {}
        urls = photo.get("urls", {}) if isinstance(photo.get("urls"), dict) else {}
        links = photo.get("links", {}) if isinstance(photo.get("links"), dict) else {}

        return CityImageResponse(
            city=city,
            configured=True,
            image_url=urls.get("regular") or urls.get("full") or urls.get("small"),
            thumb_url=urls.get("small") or urls.get("thumb"),
            alt_description=photo.get("alt_description") or photo.get("description") or f"{city} 城市图片",
            color=photo.get("color"),
            photographer_name=user.get("name"),
            photographer_url=_with_utm(user.get("links", {}).get("html") if isinstance(user.get("links"), dict) else None),
            photo_url=_with_utm(links.get("html")),
            source="unsplash",
        )


def _with_utm(url: str | None) -> str | None:
    if not url:
        return None

    settings = get_settings()
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    query.update({"utm_source": settings.unsplash_app_name, "utm_medium": "referral"})
    return urlunparse(parsed._replace(query=urlencode(query)))

