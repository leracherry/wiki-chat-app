# Wiki Chat App

Minimal chat UI with streaming and optional Wikipedia context.

## 1) Getting started

- Prereqs: Docker (or Python 3.11 + Node 18) and a Cohere API key.

Docker (recommended)
```bash
cd wiki-chat-app
# Create root env (shared defaults)
cp .env.example .env
# Optionally override per service
# echo "PROVIDER_API_KEY=YOUR_COHERE_KEY" > api/.env
# echo "VITE_API_URL=http://localhost:8000" > frontend/.env

# Build & run
docker compose up --build -d
```
- App: http://localhost:3000
- API: http://localhost:8000

Local dev (no Docker)
```bash
# API
cd wiki-chat-app/api
pip install -r requirements.txt
python main.py
# Frontend (in a new terminal)
cd ../frontend
npm install
npm run dev
```

## 2) Environment configuration (root and overrides)
This project supports layered environment files with clear precedence so you can define defaults at the repo root and override them per service.

- Root (shared): `.env`, `.env.local`
- Backend (API): `api/.env`, `api/.env.local`
- Frontend (Vite): `frontend/.env`, `frontend/.env.local`, plus mode-specific variants (e.g. `.env.development`)

Precedence (lowest → highest):
1) repo-root/.env
2) repo-root/.env.local
3) api/.env or frontend/.env
4) api/.env.local or frontend/.env.local
5) Process env and explicit docker-compose environment entries

Notes
- Docker Compose loads `./.env` first, then service-level env files (`./api/.env`, `./frontend/.env`). Values later in the list override earlier ones.
- The backend (FastAPI) also loads env files in the order above at process start.
- The frontend (Vite) loads root env first (via vite.config.ts), then standard Vite env resolution so `frontend/.env*` can override.

Root .env example
```env
# Backend
PROVIDER_API_KEY=your-provider-key-here
DEFAULT_MODEL=command-r-plus
LOG_LEVEL=INFO
PORT=8000

# Frontend
VITE_API_URL=http://localhost:8000
```

Common overrides
```bash
# Backend only override
echo "PROVIDER_API_KEY=YOUR_REAL_KEY" > api/.env
# Frontend only override
echo "VITE_API_URL=http://wiki-chat-api:8000" > frontend/.env
```

## 3) Design decisions & limitations
- SSE streaming for simplicity; no client→server backpressure.
- Thin provider wrapper + one Wikipedia tool; English-only, no caching.
- Clean URLs (only chatId); initial message via router state; refresh won't re-send.
- Dev containers only (no TLS/reverse proxy/CDN in compose).

## 4) Before exposing to customers
- Add auth, strict CORS, and a secrets manager.
- Retries/timeouts, rate limits, and basic WAF.
- Logs/metrics/traces with SLOs and alerts.
- Persist chats; unit/integration/e2e tests; feature flags.
- CDN + TLS via reverse proxy; CI/CD.

## 5) Resources used
- Cohere Tool Use: https://docs.cohere.com/v2/docs/tool-use-overview
- MediaWiki Search API: https://www.mediawiki.org/wiki/API:Search
- React Router, Vite, TailwindCSS
- Docker multi-stage builds: https://docs.docker.com/develop/develop-images/multistage-build/
