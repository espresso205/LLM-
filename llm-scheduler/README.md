# LLM Scheduler

**Cloud-Native Distributed LLM Inference Scheduling Platform**

A production-grade, microservice-based platform for managing and load-balancing Large Language Model inference requests across multiple GPU nodes. Built with FastAPI, Vue.js, and Docker.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Features](#core-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Docker Compose Deployment](#docker-compose-deployment)
  - [Local Development](#local-development)
- [Service Details](#service-details)
  - [Gateway](#gateway)
  - [Scheduler](#scheduler)
  - [Inference Node](#inference-node)
  - [Monitoring](#monitoring)
- [Load Balancing Strategies](#load-balancing-strategies)
- [Authentication & Authorization](#authentication--authorization)
- [Observability](#observability)
- [API Reference](#api-reference)
- [Scripts](#scripts)
- [Configuration Reference](#configuration-reference)
- [License](#license)

---

## Architecture Overview

```
                          ┌──────────────┐
                          │   Client /   │
                          │  Vue.js SPA  │
                          └──────┬───────┘
                                 │ HTTPS
                          ┌──────▼───────┐
                          │   Gateway    │  :8080
                          │  (FastAPI)   │
                          │  JWT Auth    │
                          │  Retry Logic │
                          └──┬───────┬───┘
                             │       │
              ┌──────────────┘       └──────────────┐
              │                                     │
       ┌──────▼──────┐                      ┌───────▼──────┐
       │  Scheduler  │  :8001               │  Monitoring  │  :8002
       │  (FastAPI)  │                      │  (FastAPI)   │
       │  Strategies │                      │  Metrics     │
       │  Registry   │                      │  Alerting    │
       └──────┬──────┘                      └──────────────┘
              │
     ┌────────┼────────┐
     │        │        │
┌────▼───┐ ┌──▼────┐ ┌─▼──────┐
│ Node-1 │ │ Node-2│ │ Node-N │  :8003+
│(Proxy) │ │(Proxy)│ │(Proxy) │
└───┬────┘ └───┬───┘ └───┬────┘
    │          │         │
┌───▼────┐ ┌──▼─────┐ ┌─▼──────┐
│ vLLM-1 │ │ vLLM-2 │ │ vLLM-N │
│ (GPU)  │ │ (GPU)  │ │ (GPU)  │
└────────┘ └────────┘ └────────┘
```

**Request Flow:**

1. Client sends a chat completion request to the **Gateway** with a JWT token.
2. Gateway authenticates the user and forwards the request to the **Scheduler**.
3. Scheduler selects an optimal **Inference Node** using the active load balancing strategy.
4. Gateway proxies the request to the chosen node, which forwards it to its local **vLLM** backend.
5. On failure, Gateway retries with automatic node exclusion and exponential backoff (up to 3 attempts).
6. **Monitoring** service continuously scrapes metrics from all services and evaluates alert rules.

---

## Core Features

| Feature | Description |
|---------|-------------|
| **Multi-Strategy Load Balancing** | Round Robin, Least Connections, Weighted Round Robin — hot-swappable at runtime via API |
| **Automatic Node Discovery** | Nodes self-register with the scheduler via heartbeat protocol with TTL-based eviction |
| **JWT Authentication** | Role-based access control (admin/user) with bcrypt password hashing |
| **Automatic Retry & Failover** | Exponential backoff retry with node exclusion on 502/503/504 errors |
| **Real-Time Monitoring** | Prometheus-compatible metrics collection with configurable alert rules |
| **Grafana Dashboards** | Pre-configured dashboards for system-wide observability |
| **Auto Model Resolution** | Transparently resolves `"auto"` model names from vLLM backends |
| **Containerized Deployment** | Multi-stage Docker builds with Docker Compose orchestration |
| **Vue.js Management UI** | Each service includes a built-in SPA for administration and monitoring |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **API Framework** | FastAPI (Python 3.11) |
| **Async Runtime** | Uvicorn with uvloop |
| **Database** | SQLite (aiosqlite) with WAL mode |
| **Authentication** | JWT (python-jose) + bcrypt (passlib) |
| **HTTP Client** | httpx (async) |
| **Metrics** | prometheus_client |
| **Visualization** | Grafana + Prometheus |
| **Frontend** | Vue 3 + Vite + Element Plus + Pinia |
| **Containerization** | Docker multi-stage builds + Docker Compose |
| **LLM Backend** | vLLM (compatible with any OpenAI API endpoint) |

---

## Project Structure

```
llm-scheduler/
├── gateway/                    # API Gateway service
│   ├── app/
│   │   ├── main.py            # FastAPI application entry
│   │   ├── auth.py            # JWT + bcrypt authentication
│   │   ├── config.py          # Pydantic settings
│   │   ├── database.py        # Async SQLite with auto-seeding
│   │   ├── retry.py           # Retry logic with node exclusion
│   │   └── routers/
│   │       ├── auth.py        # /auth/* endpoints
│   │       ├── inference.py   # /v1/chat/completions proxy
│   │       ├── history.py     # Request history CRUD
│   │       └── admin.py       # Admin user management
│   ├── frontend/              # Vue 3 SPA
│   ├── Dockerfile             # Multi-stage build (Node → Python)
│   └── requirements.txt
│
├── scheduler/                  # Load balancer & node registry
│   ├── app/
│   │   ├── main.py            # FastAPI application entry
│   │   ├── registry.py        # In-memory node registry with TTL eviction
│   │   ├── auth.py            # Internal token verification
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── routers/
│   │   │   ├── nodes.py       # Node registration & heartbeat
│   │   │   ├── schedule.py    # Scheduling decision endpoint
│   │   │   └── logs.py        # Scheduling log query
│   │   └── strategies/
│   │       ├── base.py        # Abstract strategy interface
│   │       ├── manager.py     # Strategy registry & hot-swap
│   │       ├── round_robin.py
│   │       ├── least_connections.py
│   │       └── weighted.py
│   ├── frontend/
│   ├── Dockerfile
│   └── requirements.txt
│
├── inference-node/             # Proxy to vLLM backend
│   ├── app/
│   │   ├── main.py            # FastAPI application entry
│   │   ├── vllm_client.py     # Async httpx wrapper for vLLM
│   │   ├── heartbeat.py       # Self-registration + heartbeat loop
│   │   ├── config.py
│   │   ├── database.py
│   │   └── routers/
│   │       ├── inference.py   # /v1/chat/completions proxy
│   │       ├── health.py      # Health & model info
│   │       └── logs.py        # Inference log query
│   ├── frontend/
│   ├── Dockerfile
│   └── requirements.txt
│
├── monitoring/                 # Metrics collection & alerting
│   ├── app/
│   │   ├── main.py            # FastAPI application entry
│   │   ├── collector.py       # Background metrics scraper
│   │   ├── alerts.py          # Alert rule evaluator
│   │   ├── config.py
│   │   ├── database.py
│   │   └── routers/
│   │       ├── metrics.py     # Metrics query API
│   │       └── alerts.py      # Alert rule CRUD
│   ├── frontend/
│   ├── Dockerfile
│   └── requirements.txt
│
├── shared/                     # Cross-service shared library
│   ├── models.py              # Pydantic schemas (single source of truth)
│   ├── metrics.py             # Prometheus collectors & helpers
│   ├── exceptions.py          # Custom exception types
│   └── utils.py               # Logging & timing utilities
│
├── scripts/                    # Dev & test tooling
│   ├── start_local.py         # Local dev launcher (all services)
│   ├── install_deps.py        # Dependency installer
│   ├── test_e2e.py            # End-to-end smoke tests
│   └── benchmark.py           # Concurrent load benchmark
│
├── deploy/                     # Production deployment configs
│   └── prometheus/
│       ├── docker-compose.yml  # Prometheus + Grafana stack
│       ├── prometheus.yml      # Scrape configuration
│       └── grafana/            # Pre-configured dashboards
│
├── docker-compose.yml          # Main orchestration file
└── report/                     # Academic report generator (python-docx)
```

---

## Quick Start

### Prerequisites

- **Python** 3.11+
- **Node.js** 20+ (for frontend builds)
- **Docker** & **Docker Compose** (for containerized deployment)
- A running **vLLM** instance serving an OpenAI-compatible API

### Docker Compose Deployment

```bash
# Clone the repository
git clone https://github.com/<your-username>/llm-scheduler.git
cd llm-scheduler

# Configure environment variables
cp .env.example .env
# Edit .env with your secrets and vLLM URL

# Start all services
docker compose up --build -d

# Verify all services are healthy
docker compose ps
```

Services will be available at:

| Service | URL |
|---------|-----|
| Gateway (main entry) | http://localhost:8080 |
| Scheduler | http://localhost:8001 |
| Monitoring | http://localhost:8002 |
| Inference Node 1 | http://localhost:8003 |
| Inference Node 2 | http://localhost:8004 |

**Default credentials:** `admin` / `admin123`

### Local Development

```bash
# Install Python dependencies for all services
python scripts/install_deps.py

# Start all services in separate processes
python scripts/start_local.py

# Run end-to-end tests
python scripts/test_e2e.py

# Run load benchmark
python scripts/benchmark.py --requests 20
```

---

## Service Details

### Gateway

**Port:** 8080 | **Entry Point:** `gateway/app/main.py`

The API gateway is the single external-facing service. It handles:

- **Authentication:** JWT-based user login/registration with bcrypt password hashing
- **Request Proxying:** Forwards chat completion requests through the scheduler to inference nodes
- **Retry Logic:** Automatic retry with exponential backoff (3 attempts) and node exclusion on failure
- **Request Logging:** Full request/response lifecycle tracking in SQLite
- **Admin APIs:** User management endpoints for administrators
- **Metrics:** Real-time QPS, latency percentiles, and error rates

### Scheduler

**Port:** 8001 | **Entry Point:** `scheduler/app/main.py`

The central load balancer that manages node registration and request scheduling:

- **Node Registry:** In-memory registry with async-safe locking and TTL-based stale node eviction
- **Strategy Engine:** Pluggable scheduling strategies with runtime hot-swap (no restart required)
- **Decision Logging:** Every scheduling decision is recorded with algorithm used, candidates, latency, and active connections
- **Health Monitoring:** Background task evicts nodes that miss heartbeat deadlines (default 30s)

### Inference Node

**Port:** 8003 (configurable) | **Entry Point:** `inference-node/app/main.py`

A thin proxy service connecting to a local vLLM backend:

- **Self-Registration:** Automatically registers with the scheduler on startup with exponential backoff retry
- **Heartbeat:** Periodic health reports including active connection count and GPU metrics
- **vLLM Proxy:** Forwards chat completion requests to vLLM, with automatic model name resolution
- **Connection Tracking:** Atomic counter for active concurrent requests

### Monitoring

**Port:** 8002 | **Entry Point:** `monitoring/app/main.py`

Centralized metrics collection and alerting:

- **Metrics Scraping:** Background loop pulls `/metrics/json` from all services every 15 seconds
- **Dynamic Node Discovery:** Automatically discovers new inference nodes from the scheduler
- **Alert Engine:** Configurable alert rules evaluated against collected metrics (latency, error rate, QPS, connections)
- **Event Bus:** Receives and stores events from all services for audit trail

---

## Load Balancing Strategies

All strategies implement the `SchedulingStrategy` abstract base class and can be switched at runtime via `PUT /api/strategy`.

| Strategy | Algorithm | Best For |
|----------|-----------|----------|
| **Round Robin** (`round_robin`) | Cyclic counter-based selection across healthy nodes | Uniform node hardware, equal-load scenarios |
| **Least Connections** (`least_connections`) | Selects the node with the fewest active connections | Heterogeneous workloads, variable request duration |
| **Weighted Round Robin** (`weighted`) | Probabilistic selection weighted by node weight | Nodes with different GPU capacities |

**Switching strategies at runtime:**

```bash
curl -X PUT http://localhost:8001/api/strategy \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: internal-secret-change-me" \
  -d '{"strategy": "least_connections"}'
```

**Extending with a custom strategy:**

1. Create a new class inheriting from `SchedulingStrategy` in `scheduler/app/strategies/`.
2. Implement the `async pick(nodes: List[NodeInfo]) -> NodeInfo` method.
3. Register it in `scheduler/app/strategies/manager.py`.

---

## Authentication & Authorization

The system implements a two-tier security model:

### External Authentication (Gateway)

- **JWT tokens** with configurable expiration (default: 60 minutes)
- **bcrypt** password hashing via passlib
- **Role-based access:** `admin` (full access) and `user` (inference + own history)
- Admin account is auto-seeded on first startup

### Internal Authentication (Service-to-Service)

- **Shared internal token** (`INTERNAL_TOKEN`) secures all inter-service communication
- Scheduler, Monitoring, and Inference Nodes verify this token on every internal API call
- Token is passed via the `X-Internal-Token` header

---

## Observability

### Prometheus Metrics

Every service exposes a `/metrics` endpoint with Prometheus-format metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `llm_inference_requests_total` | Counter | Total inference requests by service, model, status |
| `llm_tokens_total` | Counter | Token throughput by service and type |
| `llm_inference_latency_seconds` | Histogram | End-to-end inference latency |
| `llm_schedule_decisions_total` | Counter | Scheduling decisions by algorithm and node |
| `llm_schedule_decision_seconds` | Histogram | Scheduling decision latency (sub-10ms typical) |
| `llm_node_active_connections` | Gauge | Active connections per node |
| `llm_node_status` | Gauge | Node health status (1=healthy, 0=unhealthy) |

### Grafana Dashboards

Pre-configured Grafana provisioning is included in `deploy/prometheus/grafana/`:

- **LLM Overview Dashboard:** System-wide QPS, latency percentiles, error rates, node health, and token throughput
- **Auto-provisioned datasource:** Prometheus connected on startup

To launch the observability stack:

```bash
cd deploy/prometheus
docker compose up -d
```

- Grafana: http://localhost:3000 (`admin` / `admin`)
- Prometheus: http://localhost:9090

### Alerting

The monitoring service includes a built-in alert engine that evaluates user-defined rules against collected metrics:

```bash
# Create an alert rule
curl -X POST http://localhost:8002/api/alerts/rules \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: internal-secret-change-me" \
  -d '{
    "name": "High Latency",
    "metric": "latency_p95",
    "operator": "gt",
    "threshold": 10.0,
    "window_s": 250
  }'
```

---

## API Reference

### Gateway Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/register` | Public | Register a new user |
| `POST` | `/auth/login` | Public | Obtain JWT token |
| `POST` | `/v1/chat/completions` | User | Submit inference request (OpenAI-compatible) |
| `GET` | `/api/history` | User | Get own request history |
| `GET` | `/api/admin/users` | Admin | List all users |
| `GET` | `/metrics/json` | Internal | JSON metrics for monitoring scraper |
| `GET` | `/health` | Public | Health check |

### Scheduler Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/nodes/register` | Internal | Register an inference node |
| `POST` | `/api/nodes/{id}/heartbeat` | Internal | Node heartbeat |
| `DELETE` | `/api/nodes/{id}/deregister` | Internal | Remove a node |
| `GET` | `/api/nodes` | Internal | List all registered nodes |
| `POST` | `/api/schedule` | Internal | Get scheduling decision |
| `GET` | `/api/strategy` | Internal | Get current strategy |
| `PUT` | `/api/strategy` | Internal | Switch strategy |
| `GET` | `/api/logs/scheduling` | Internal | Query scheduling logs |

### Inference Node Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/v1/chat/completions` | Internal | Forward to vLLM |
| `GET` | `/api/health` | Internal | Node health + vLLM status |
| `GET` | `/api/model` | Internal | Model info from vLLM |

### Monitoring Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/metrics/summary` | Internal | Aggregated metrics summary |
| `GET` | `/api/metrics/timeseries` | Internal | Time series data |
| `GET` | `/api/metrics/nodes` | Internal | Per-node statistics |
| `GET` | `/api/alerts/rules` | Internal | List alert rules |
| `POST` | `/api/alerts/rules` | Internal | Create alert rule |
| `GET` | `/api/alerts/events` | Internal | List fired alerts |
| `POST` | `/api/events` | Internal | Receive event from services |

---

## Scripts

| Script | Usage | Description |
|--------|-------|-------------|
| `start_local.py` | `python scripts/start_local.py` | Starts all 4 services locally with hot-reload, port conflict detection, and graceful shutdown |
| `install_deps.py` | `python scripts/install_deps.py` | Installs Python dependencies for all services |
| `test_e2e.py` | `python scripts/test_e2e.py [--base-url URL]` | End-to-end smoke tests covering auth, inference, RBAC, and scheduler |
| `benchmark.py` | `python scripts/benchmark.py [-n 20] [--strategy all]` | Concurrent load benchmark comparing all scheduling strategies with colored output |

---

## Configuration Reference

All services use **Pydantic Settings** with environment variable and `.env` file support.

### Gateway

| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEDULER_URL` | `http://localhost:8001` | Scheduler service URL |
| `MONITORING_URL` | `http://localhost:8002` | Monitoring service URL |
| `DATABASE_URL` | `gateway.db` | SQLite database path |
| `SECRET_KEY` | *(change in production)* | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT token lifetime |
| `INTERNAL_TOKEN` | *(change in production)* | Inter-service auth token |
| `ADMIN_USERNAME` | `admin` | Default admin username |
| `ADMIN_PASSWORD` | `admin123` | Default admin password |
| `PORT` | `8080` | Service port |

### Scheduler

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `scheduler.db` | SQLite database path |
| `HEARTBEAT_TIMEOUT_S` | `30` | Seconds before stale node eviction |
| `DEFAULT_STRATEGY` | `round_robin` | Initial scheduling strategy |
| `INTERNAL_TOKEN` | *(change in production)* | Inter-service auth token |
| `PORT` | `8001` | Service port |

### Inference Node

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_ID` | `node-1` | Unique node identifier |
| `NODE_HOST` | `localhost` | Node hostname |
| `NODE_PORT` | `8003` | Node service port |
| `VLLM_URL` | `http://localhost:8000` | vLLM backend URL |
| `SCHEDULER_URL` | `http://localhost:8001` | Scheduler URL for registration |
| `MONITORING_URL` | `http://localhost:8002` | Monitoring URL for events |
| `HEARTBEAT_INTERVAL_S` | `10` | Heartbeat interval in seconds |
| `INTERNAL_TOKEN` | *(change in production)* | Inter-service auth token |

### Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `monitoring.db` | SQLite database path |
| `GATEWAY_URL` | `http://localhost:8080` | Gateway metrics source |
| `SCHEDULER_URL` | `http://localhost:8001` | Scheduler metrics source |
| `NODE_URLS` | *(empty)* | Comma-separated node URLs |
| `SCRAPE_INTERVAL_S` | `15` | Metrics scrape interval |
| `INTERNAL_TOKEN` | *(change in production)* | Inter-service auth token |
| `PORT` | `8002` | Service port |

---

## License

This project is available for educational and research purposes.
