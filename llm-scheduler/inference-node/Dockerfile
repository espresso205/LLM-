FROM node:20-alpine AS frontend
WORKDIR /ui
COPY inference-node/frontend/package.json ./
RUN npm config set registry https://registry.npmmirror.com && npm install
COPY inference-node/frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] httpx aiosqlite pydantic-settings \
    prometheus_client pydantic>=2.0

COPY shared/ /app/shared/

COPY inference-node/app/ ./app/
COPY --from=frontend /app/static ./app/static/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
