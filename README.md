# 智能旅行助手

一个前后端分离的智能旅行助手示例项目。后端使用 FastAPI、Pydantic 和异步多 Agent 编排；前端使用 Vue 3、TypeScript、Vite、Ant Design Vue、Axios、Vue Router、AMap JSAPI、html2canvas 和 jsPDF。

## 项目结构

```text
TravelAgent/
  backend/   FastAPI + Pydantic + 多 Agent 编排
  frontend/  Vue 3 + TypeScript + Vite 旅行规划界面
```

## 后端启动

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

后端默认地址：`http://127.0.0.1:8000`

## 前端启动

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

前端默认地址：`http://127.0.0.1:5173`

## 高德 MCP

后端没有把高德能力注册成 LLM tool，而是通过 `backend/app/agents/amap_mcp.py` 的 MCP 适配层调用官方 MCP 服务。没有配置 MCP 时，系统会返回可用于开发联调的示例数据。

复制 `backend/.env.example` 为 `backend/.env` 后按需配置：

```env
AMAP_MCP_ENDPOINT=http://127.0.0.1:8765/mcp
AMAP_MCP_SEARCH_TOOL=maps_text_search
AMAP_MCP_WEATHER_TOOL=maps_weather
AMAP_MCP_DETAIL_TOOL=maps_search_detail
```

`AMAP_MAPS_API_KEY` 放后端，不放前端。这个 Key 只给 MCP server 用。

## Unsplash

城市图片通过后端代理 `GET /api/media/city-image` 拉取。你只需要在 `backend/.env` 里填 `UNSPLASH_ACCESS_KEY`，不用填 Secret Key，也不要放到前端。

## LLM

LLM 预留配置在 `backend/.env`：

```env
LLM_PROVIDER=aihubmix
LLM_BASE_URL=https://aihubmix.com/v1
LLM_API_KEY=
LLM_MODEL=xiaomi-mimo-v2-omni-free
```

当前项目先把 Agent 编排、Pydantic 校验和外部数据接通，LLM 接口位已经留好，后面可以直接接到这些配置。
可以通过 `GET /api/llm/health` 验证 AIHubMix 是否连通。

前端地图需要配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_AMAP_KEY=你的高德 Web JS API Key
VITE_AMAP_SECURITY_JS_CODE=你的安全密钥
```

## 核心流程

1. `TravelRequest` 进入 FastAPI。
2. Pydantic 从 `Location`、`Attraction`、`Hotel`、`Meal`、`DayTrip` 到 `TripPlan` 逐层校验。
3. 景点搜索 Agent、天气查询 Agent、酒店推荐 Agent 使用 `asyncio.gather` 并行执行。
4. 计划规划 Agent 汇总前三个 Agent 的结构化结果，生成完整 `TripPlan`。
5. 前端展示进度条、预算、可编辑行程、侧边锚点、地图预览和 PDF 导出。
