from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "智能旅行助手"
    app_env: str = "development"
    frontend_origin: str = "http://127.0.0.1:5173"

    amap_mcp_endpoint: str | None = None
    amap_mcp_command: str = "npx.cmd"
    amap_mcp_args: str = "-y @amap/amap-maps-mcp-server"
    amap_maps_api_key: str | None = None
    amap_mcp_search_tool: str = Field(default="maps_text_search")
    amap_mcp_weather_tool: str = Field(default="maps_weather")
    amap_mcp_detail_tool: str = Field(default="maps_search_detail")

    unsplash_access_key: str | None = None
    unsplash_app_name: str = "travel_agent"

    llm_provider: str = "openai_compatible"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    return Settings()
