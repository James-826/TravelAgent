from __future__ import annotations

import asyncio
import json
import os
import shlex
from asyncio.subprocess import PIPE
from typing import Any
from uuid import uuid4

import httpx

from app.core.config import get_settings


_STDIO_SEMAPHORE = asyncio.Semaphore(3)
_TOOL_TIMEOUT_SECONDS = 12
_DETAIL_TIMEOUT_SECONDS = 8


class AmapMCPClient:
    """Adapter for the official AMap MCP server.

    It supports two modes:
    1. AMAP_MCP_ENDPOINT: an HTTP JSON-RPC bridge.
    2. AMAP_MAPS_API_KEY + AMAP_MCP_COMMAND/ARGS: stdio MCP through npx.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.amap_mcp_endpoint or self.settings.amap_maps_api_key)

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
        if self.settings.amap_mcp_endpoint:
            return await self._call_http_tool(tool_name, arguments)
        if self.settings.amap_maps_api_key:
            return await self._call_stdio_tool(tool_name, arguments)
        return None

    async def _call_http_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": uuid4().hex,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(self.settings.amap_mcp_endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data.get("result", {})

    async def _call_stdio_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        async with _STDIO_SEMAPHORE:
            return await self._call_stdio_tool_unlocked(tool_name, arguments)

    async def _call_stdio_tool_unlocked(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        command = _windows_command(self.settings.amap_mcp_command)
        args = shlex.split(self.settings.amap_mcp_args, posix=False)
        env = os.environ.copy()
        env["AMAP_MAPS_API_KEY"] = self.settings.amap_maps_api_key or ""

        process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            env=env,
        )
        try:
            await _write_mcp_message(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "travel-agent-backend", "version": "0.1.0"},
                    },
                },
            )
            init_response = await _read_until_id(process, 1)
            if "error" in init_response:
                raise RuntimeError(init_response["error"])

            await _write_mcp_message(
                process,
                {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            )
            await _write_mcp_message(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
            )
            tool_response = await _read_until_id(process, 2)
            if "error" in tool_response:
                raise RuntimeError(tool_response["error"])
            return tool_response.get("result", {})
        finally:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except TimeoutError:
                process.kill()

    async def search_pois(self, city: str, keyword: str) -> list[dict[str, Any]]:
        result = await _call_with_timeout(
            self.call_tool(
                self.settings.amap_mcp_search_tool,
                {"city": city, "keywords": keyword},
            ),
            _TOOL_TIMEOUT_SECONDS,
        )
        pois = _extract_list(_decode_mcp_payload(result or {}))
        if pois:
            if any(not poi.get("location") for poi in pois):
                rest_pois = await self._search_pois_rest(city, keyword)
                if rest_pois:
                    return rest_pois
            return pois
        return await self._search_pois_rest(city, keyword)

    async def get_weather(self, city: str) -> dict[str, Any] | None:
        result = await _call_with_timeout(
            self.call_tool(self.settings.amap_mcp_weather_tool, {"city": city}),
            _TOOL_TIMEOUT_SECONDS,
        )
        decoded = _decode_mcp_payload(result or {})
        return decoded if isinstance(decoded, dict) else None

    async def get_poi_detail(self, poi_id: str) -> dict[str, Any] | None:
        if not poi_id:
            return None
        result = await _call_with_timeout(
            self.call_tool(self.settings.amap_mcp_detail_tool, {"id": poi_id}),
            _DETAIL_TIMEOUT_SECONDS,
        )
        decoded = _decode_mcp_payload(result or {})
        if isinstance(decoded, dict) and decoded.get("location"):
            return decoded
        return await self._get_poi_detail_rest(poi_id)

    async def _search_pois_rest(self, city: str, keyword: str) -> list[dict[str, Any]]:
        if not self.settings.amap_maps_api_key:
            return []
        params = {
            "key": self.settings.amap_maps_api_key,
            "keywords": keyword,
            "city": city,
            "citylimit": "false",
            "extensions": "all",
        }
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get("https://restapi.amap.com/v3/place/text", params=params)
            response.raise_for_status()
            data = response.json()
        if data.get("status") != "1":
            return []
        return [item for item in data.get("pois", []) if isinstance(item, dict)]

    async def _get_poi_detail_rest(self, poi_id: str) -> dict[str, Any] | None:
        if not self.settings.amap_maps_api_key:
            return None
        params = {"key": self.settings.amap_maps_api_key, "id": poi_id}
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get("https://restapi.amap.com/v3/place/detail", params=params)
            response.raise_for_status()
            data = response.json()
        if data.get("status") != "1" or not data.get("pois"):
            return None
        poi = data["pois"][0]
        return poi if isinstance(poi, dict) else None


async def _write_mcp_message(process: asyncio.subprocess.Process, payload: dict[str, Any]) -> None:
    if not process.stdin:
        raise RuntimeError("MCP stdin is unavailable")

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n"
    process.stdin.write(body)
    await process.stdin.drain()


async def _read_until_id(process: asyncio.subprocess.Process, expected_id: int) -> dict[str, Any]:
    while True:
        message = await asyncio.wait_for(_read_mcp_message(process), timeout=30)
        if message.get("id") == expected_id:
            return message


async def _read_mcp_message(process: asyncio.subprocess.Process) -> dict[str, Any]:
    if not process.stdout:
        raise RuntimeError("MCP stdout is unavailable")

    while True:
        line = await process.stdout.readline()
        if not line:
            stderr = await _read_stderr(process)
            raise RuntimeError(f"MCP server closed stdout. {stderr}")
        text = line.decode("utf-8", errors="ignore").strip()
        if not text:
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue


async def _read_stderr(process: asyncio.subprocess.Process) -> str:
    if not process.stderr:
        return ""
    try:
        data = await asyncio.wait_for(process.stderr.read(), timeout=0.2)
    except TimeoutError:
        return ""
    return data.decode("utf-8", errors="ignore")


def _decode_mcp_payload(result: dict[str, Any]) -> Any:
    content = result.get("content", result)
    if isinstance(content, list):
        text_parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        if text_parts:
            text = "\n".join(text_parts).strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
    return content


def _extract_list(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    if isinstance(result, dict):
        for key in ("pois", "data", "items", "results"):
            value = result.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _windows_command(command: str) -> str:
    if os.name == "nt" and command == "npx":
        return "npx.cmd"
    return command


async def _call_with_timeout(coro, timeout: int) -> dict[str, Any] | None:
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except (asyncio.TimeoutError, RuntimeError, httpx.HTTPError):
        return None
