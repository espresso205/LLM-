# ── Stage 1: Build Vue frontend ──────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /ui
COPY gateway/frontend/package.json ./
RUN npm config set registry https://registry.npmmirror.com && npm install
COPY gateway/frontend/ ./
RUN npm run build
# vite outputs to ../app/static → /app/static

# ── Stage 2: Python service ───────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] httpx aiosqlite pydantic-settings \
    python-jose[cryptography] passlib[bcrypt] python-multipart \
    prometheus_client pydantic>=2.0 bcrypt==4.0.1

COPY shared/ /app/shared/

COPY gateway/app/ ./app/
COPY --from=frontend /app/static ./app/static/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
