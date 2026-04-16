FROM node:20-alpine AS frontend
WORKDIR /ui
COPY scheduler/frontend/package.json ./
RUN npm config set registry https://registry.npmmirror.com && npm install
COPY scheduler/frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] httpx aiosqlite pydantic-settings \
    prometheus_client pydantic>=2.0

COPY shared/ /app/shared/

COPY scheduler/app/ ./app/
COPY --from=frontend /app/static ./app/static/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
