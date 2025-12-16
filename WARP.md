# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project overview
- Full-stack app with a React (Vite) SPA in the repo root and a FastAPI backend in server/.
- Docker image builds the frontend and serves the compiled assets from the FastAPI app (server/static). PostgreSQL is used for persistence with SQLAlchemy models plus raw SQL migrations.

Common commands
- Frontend (Vite + React)
  - Install deps
    ```bash path=null start=null
    npm install
    ```
  - Dev server (Vite on 5173)
    ```bash path=null start=null
    npm run dev
    ```
  - Build static assets into dist/
    ```bash path=null start=null
    npm run build
    ```
  - Preview production build
    ```bash path=null start=null
    npm run preview
    ```
  - Lint
    ```bash path=null start=null
    npm run lint
    ```

- Backend (FastAPI)
  - Install deps
    ```bash path=null start=null
    pip install -r server/requirements.txt
    ```
  - Run with reload (recommended for local dev)
    ```bash path=null start=null
    uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
    ```
  - Alternative (entrypoint in main.py)
    ```bash path=null start=null
    python server/main.py
    ```

- Docker and Postgres
  - Build and run app + Postgres (applies DB init/migrate SQL)
    ```bash path=null start=null
    docker-compose up --build
    ```
  - Rebuild after code changes
    ```bash path=null start=null
    docker-compose up --build --force-recreate
    ```

- Tests
  - No test scripts or configs are present in this repo at the time of writing.

Architecture and code structure
- Frontend (React + Vite)
  - Location: src/
  - Routing and auth: src/App.jsx wires ProtectedRoute and page-level routes (Dashboard, CreateCampaign, Analytics, IdeaGenerator, Settings, Pricing, HelpSupport). src/main.jsx wraps with BrowserRouter, ThemeProvider, and Sonner Toaster. Vite configuration (vite.config.js) enables host 0.0.0.0 and polling for reliable HMR across environments.
  - Build/serve: npm run build creates dist/ which Docker copies into server/static; the FastAPI app serves these assets and a catch-all route returns static/index.html for SPA routing.

- Backend (FastAPI)
  - Entry: server/main.py
    - App lifecycle: lifespan context initializes DB and a background scheduler (server/scheduler_service.py) on startup and shuts them down on exit.
    - Static and uploads: Serves built frontend from /static and exposes /public for generated/uploaded images (create_placeholder_image, upload_custom_image). A custom /public/{filename} handler deals with URL-encoded names.
    - Routers: Includes google_complete, dashboard_routes, social_media_routes (platform connect/status and OAuth flows), auth_routes (Google OAuth + JWT), idea_generator_routes.
    - Generative features: Caption providers (Groq, OpenAI) and image providers (Stability, OpenAI, PiAPI). Fallbacks generate placeholder images if providers are unavailable.
    - Batch generation and scheduling: Endpoints generate multiple posts, store drafts, and compute or apply schedules; database writes go through server/database_service.py.
    - Analytics: Facebook/Twitter/Instagram/Reddit analytics endpoints with graceful fallbacks when credentials are missing.
    - SPA serving: A catch-all GET /{path} responds with static/index.html unless the path conflicts with API routes.

- Database
  - Access layers: Mixed async (databases) and sync (SQLAlchemy sessions) via server/database.py (DatabaseManager, SessionLocal, Base). Business logic in server/database_service.py; calendar operations in server/calendar_service.py.
  - Models: server/models.py defines User, Campaign, Post (multi-platform via platforms TEXT[]/ARRAY), Image, Caption, PostingSchedule, BatchOperation, CalendarEvent, and ApiUsage Pydantic response models.
  - Schema and migrations: server/database_schema.sql contains the canonical schema; top-level init-db.sql and migrate-db.sql are mounted into the Postgres container to initialize and evolve tables and triggers (e.g., auto-creating calendar_events for scheduled posts). server/database.py can also run schema and follow-up migrations at app startup.

- Background scheduler
  - server/scheduler_service.py runs a loop that fetches due posts and publishes to configured platforms using platform adapters (facebook_poster/facebook_manager, twitter_service, reddit_service, instagram_service) and image path converters. It updates status per-platform and marks failures appropriately.

- Auth and identity
  - Google sign-in: server/auth_service.py verifies Google ID tokens (client ID currently set in code) and issues JWTs (JWT_SECRET env). server/auth_routes.py exposes /auth/google and /auth/me plus a dependency get_current_user_dependency used across protected routes.

- Social platform connections
  - server/social_media_routes.py offers per-platform status and connect/disconnect flows. It uses env_manager to persist credentials and provides OAuth redirects for Facebook/Instagram and Reddit. It returns connection diagnostics and supports multi-account patterns for some platforms.

- Serving the frontend from the backend
  - Dockerfile builds the React app (Stage 1) and copies dist/ to server/static (Stage 2). server/main.py mounts /assets and /icons and a catch-all route that returns static/index.html for unknown paths, enabling SPA routing.
  - When running the backend without Docker, build the frontend first so static/index.html exists; otherwise, only API routes will work.

Environment and configuration highlights
- docker-compose.yml: Spins up Postgres and the app, maps server/public and server/.env, and passes many platform/API keys (e.g., GROQ_API_KEY, STABILITY_API_KEY, CHATGPT_API, NANO_BANANA_API_KEY, JWT_SECRET, and provider-specific tokens). It also mounts Credentials.json read-only if needed by Google integrations.
- Vite dev server (npm run dev) is separate from the backend; during Docker builds the frontend is compiled then served from the backend.

Tips for working efficiently here
- Frontend/Backend split dev: Run npm run dev for the SPA and uvicorn server.main:app --reload for the API to iterate quickly; Docker is best for an integrated, production-like run with Postgres and static assets.
- Image paths: Generated images are written under server/public with API responses returning /public/filename; FastAPI’s /public route serves these files.
