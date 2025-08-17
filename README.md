# Wiki Chat App

Minimal chat UI with streaming and optional Wikipedia context.

## 1) Getting started

- Prereqs: Docker (or Python 3.11 + Node 18) and a Cohere API key.

Docker (recommended)
```bash
cd wiki-chat-app
# Copy defaults and set your key
cp .env.example .env
# Optionally set per-service values
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

## 2) Environment configuration (simple)
You only need two variables for local use:
- Backend: PROVIDER_API_KEY (your Cohere API key; DEFAULT_MODEL optional)
- Frontend: VITE_API_URL (API base URL; defaults to http://localhost:8000)

Pick one of these simple setups:
- Docker Compose: put backend values in root .env or api/.env. If you need a non-default API URL for the frontend, set it in frontend/.env (Vite reads frontend/.env at build time).
- No Docker: put backend vars in api/.env and frontend vars in frontend/.env. Each app reads its own .env.

Examples
```env
# api/.env (backend)
PROVIDER_API_KEY=your-provider-key
DEFAULT_MODEL=command-r-plus
LOG_LEVEL=INFO
PORT=8000
```
```env
# frontend/.env
VITE_API_URL=http://localhost:8000
```

Notes
- Docker Compose wires env files to containers (./.env, api/.env, frontend/.env). Vite builds only read frontend/.env* files.
- The backend also accepts COHERE_API_KEY for compatibility if PROVIDER_API_KEY isn’t set.

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
