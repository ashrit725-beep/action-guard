# syntax=docker/dockerfile:1
#
# One image runs everything: the API and the website, from one address.
#   docker build -t vexen .
#   docker run -p 8000:10000 --env-file backend/.env vexen        (then open http://localhost:8000)

# ---- Stage 1: build the website (React) ------------------------------------------------
FROM node:22-bookworm-slim AS web
WORKDIR /web

# Dependencies first, so this layer is reused until package.json or yarn.lock change.
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile --non-interactive --network-timeout 300000

COPY frontend/ ./
# REACT_APP_BACKEND_URL is deliberately not set: the site then calls /api on its own address.
ENV CI=false \
    GENERATE_SOURCEMAP=false
RUN yarn build


# ---- Stage 2: the server (FastAPI), which also serves the website ----------------------
FROM python:3.12-slim-bookworm AS app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
COPY --from=web /web/build /app/frontend/build

# Run as an ordinary user, not as root.
RUN useradd --system --uid 10001 --no-create-home vexen && chown -R vexen:vexen /app
USER vexen

# Render and Railway tell the container which port to use through PORT.
ENV PORT=10000 \
    VEXEN_ENV=production
EXPOSE 10000

# One process on purpose: the rate limits and the email worker live inside it, so never
# run two copies. The shutdown allowance lets an AI request that is still running finish
# when a new version is deployed.
CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT} --workers 1 --timeout-graceful-shutdown 100 --timeout-keep-alive 120"]
