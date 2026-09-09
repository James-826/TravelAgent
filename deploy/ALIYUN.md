# Aliyun deployment — 2026-09-10

Public URL: http://47.95.124.109:8000/travel/

Build from frontend directory: `npm ci && VITE_API_BASE_URL=/travel npm run build -- --base=/travel/`.
FastAPI runs as travel user on 127.0.0.1:4181. Nginx serves built assets and forwards /travel/api/ to /api/. Single worker, systemd memory limit 320MB. Model credentials are stored in /etc/travel-agent.env (0600).

Two model validation tests passed. A two-day HTTP planning request and a three-day browser planning request returned structured itineraries with LLM-refined text. AMap/MCP and Unsplash credentials are NOT configured: attraction/hotel/weather providers fall back to authored examples, with warnings retained in the interface and exported report. These are not live location, inventory or weather results. No service availability claim is made for the map.

The source-based examples remain labeled; no fabricated business database is used. This deployment is intended for low-volume portfolio browsing.
