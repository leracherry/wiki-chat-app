# Wiki Chat App

Modern, containerized chat experience that streams model responses in real time and optionally augments answers with Wikipedia. The stack includes:
- Backend: FastAPI (Python), Cohere Chat API (provider-agnostic abstraction), SSE streaming, Wikipedia tool (MediaWiki API)
- Frontend: React + TypeScript + Vite + TailwindCSS
- Ops: Docker multi-stage builds, Docker Compose, health checks, non-root users

## Features
- Clean home → chat flow with generated chatId in URL (no query params)
- Real-time streaming via Server‑Sent Events (SSE)
- Wikipedia tool you can toggle on/off per chat
- Strong UI defaults (Tailwind, Cohere-like palette) and accessible button/focus states
- Secure-by-default Docker images (non-root), app and health checks

---

## Getting Started

### 1) Prerequisites
- Docker and Docker Compose
- A Cohere API key (set as `PROVIDER_API_KEY`)

### 2) Configure environments
- Backend API
  ```bash
  cp api/.env.example api/.env
  # Edit api/.env and set:
  # PROVIDER_API_KEY=your_key_here
  # (OPTIONAL) DEFAULT_MODEL, LOG_LEVEL, PORT
  ```
- Frontend (optional for local dev; Compose injects service URL)
  ```bash
  cp frontend/.env.example frontend/.env
  # VITE_API_URL=http://localhost:8000
  ```

### 3) Run with Docker Compose
```bash
docker compose up --build -d
```
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Health checks:
  - API: `GET http://localhost:8000/api/health`

### 4) Local development (without Docker)
- Backend
  ```bash
  cd api
  pip install -r requirements.txt
  python main.py
  # API on http://localhost:8000
  ```
- Frontend
  ```bash
  cd frontend
  npm install
  npm run dev
  # App on http://localhost:5173 (Vite default)
  ```

---

## How it works

### Flow
1) On the home page, you enter a question and (optionally) enable Wikipedia.
2) The app generates a `chatId` and navigates to `/chat/{chatId}` with a clean URL; initial data is passed via router state (not query params).
3) The chat page posts to `POST /api/chat/stream` and displays the assistant response as it streams in real time.
4) If the model decides to use the Wikipedia tool, the server performs the MediaWiki search, feeds the formatted results back to the model, and streams the final answer.

### API Endpoints
- `GET /api/health` – service health
- `POST /api/chat/stream` – SSE stream
  - Request JSON
    - `message` (string, required): user input
    - `chat_id` (string, optional): client chat id; server will emit a canonical id first
    - `use_wikipedia` (bool, default false): enable tool
    - `model`, `max_tokens`, `temperature` (optional): provider options
  - Streamed events (line-delimited `data: {...}\n\n`)
    - `{ "type": "chat_id", "chat_id": "..." }`
    - `{ "type": "tool", "query": "..." }` (notification only)
    - `{ "type": "text", "text": "chunk" }` (zero or more)
    - `{ "type": "done" }` (terminal)
    - `{ "type": "error", "error": "..." }` (terminal on error)

### Frontend Notes
- Vite + React Router v6, TailwindCSS
- Initial message is sent once via location state (not URL params)
- Wikipedia status is shown as a discrete banner with spinner—content remains clean

### Config Reference
- API (`api/.env`)
  - `PROVIDER_API_KEY` (required)
  - `DEFAULT_MODEL` (optional; e.g., `command-r-plus`)
  - `LOG_LEVEL` (default `INFO`)
  - `PORT` (default `8000`)
- Frontend (`frontend/.env` for local dev)
  - `VITE_API_URL` (default `http://localhost:8000`)

---

## Design Decisions & Limitations

### Why SSE for streaming
- Simpler to implement and proxy than WebSockets for unidirectional token streams
- Lines with `data: ...` are easy to parse and robust to partial chunks
- Limitation: No client → server backpressure; keep payloads modest

### Provider abstraction
- Thin `ProviderClient` wraps Cohere Chat API and keeps a stable surface for model params
- Tool-calling support: constructs a function tool for Wikipedia queries and loops once to include tool results
- Limitation: Tool format varies among providers; abstraction may need adapters to support others

### Wikipedia tool
- Uses MediaWiki Search and Extracts APIs via `aiohttp`
- Converts booleans to strings in query params (MediaWiki/aiohttp requirement)
- Limits extracts to ~500 chars to keep prompts small
- Limitation: English Wikipedia only; no caching; no retries/backoff on API hiccups

### URL hygiene
- Message and toggles aren’t placed in the URL; only `chatId` appears for shareability
- React Router `location.state` carries the one-shot message
- Limitation: Reloading the chat page won’t resubmit the initial message (by design)

### Containers & Ops
- Multi‑stage builds, non‑root users, health checks in both services
- Frontend serves static build via `serve` (simple and robust); Compose wires `VITE_API_URL` to the API service
- Limitation: No TLS termination or edge cache/CDN in dev compose; add a reverse proxy for real deployments

---

## What I’d change before exposing to customers
- Security & Auth
  - AuthN/Z for API; signed sessions; CSRF protections as needed
  - Strict CORS (no wildcard), proper origins per environment
  - Secrets via a manager (e.g., SSM, Vault), not plain envs in Compose
- Reliability & Scale
  - Retries/backoff and timeouts for MediaWiki & provider calls; circuit-breaking
  - Rate limiting & quotas per IP/user; WAF/DoS protections
  - Add caching layer for Wikipedia results (e.g., Redis) and HTTP caching headers
- Observability & QA
  - Structured JSON logs with trace/span IDs; metrics (Prometheus), tracing (OTel)
  - SLOs and alerts; synthetic checks for streaming endpoints
  - Expand tests (unit + integration + contract for SSE), add e2e suite (Playwright)
- Product
  - Persist conversations; pagination; export; analytics
  - Model/tool selection UI; feature flags for tools
  - Internationalization and accessibility audit
- Delivery
  - Production Dockerfiles/Compose or Helm charts; CI/CD with lint/type/test/build gates
  - CDN for frontend static assets; reverse proxy (Traefik/Nginx) with TLS

---

## Troubleshooting
- 404 at `/health` in logs: use `/api/health` (router mounted at `/api`)
- Frontend can’t reach API: confirm `VITE_API_URL` and Compose network; test `curl http://wiki-chat-api:8000/api/health` inside network
- Empty stream: check provider quota or key, and server logs for `provider.chat.stream.error`
- Wikipedia failures: intermittent rate limits; add retries/backoff or try again
- Browser cache: hard refresh (Cmd+Shift+R) after UI style changes

---

## Resources used
- Cohere Chat API & Tool Use: https://docs.cohere.com/v2/docs/tool-use-overview
- MediaWiki Search API: https://www.mediawiki.org/wiki/API:Search
- React Router (future flags): https://reactrouter.com/
- Vite: https://vitejs.dev/  • TailwindCSS: https://tailwindcss.com/
- Docker best practices: https://docs.docker.com/develop/develop-images/multistage-build/
- Programming assistant: GitHub Copilot

---

## Quick API Smoke Test
```bash
# Health
curl -s http://localhost:8000/api/health

# Stream (Wikipedia on)
curl -N -H 'Content-Type: application/json' \
  -d '{"message":"Who was the first person on the moon?","use_wikipedia":true}' \
  http://localhost:8000/api/chat/stream
```

## Project Structure (high level)
```
wiki-chat-app/
  api/                # FastAPI app, provider abstraction, Wikipedia tool
  frontend/           # React + Vite + Tailwind client
  docker-compose.yml  # Dev orchestration
```
