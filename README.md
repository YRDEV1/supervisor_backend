# Supervisor Dashboard Backend

REST API behind a dashboard for sales supervisors. It lets a supervisor see how their field sales agents, clients, orders, products and territories are doing, without opening the company's 1C accounting system.

## Why it exists

Sales data lives in 1C (the accounting/ERP system), which is slow to query and not built for dashboards. A supervisor needs quick answers to questions like:

- Which agents visited their clients today, and which clients were skipped?
- How long was an agent idle? What is their rating and order count?
- What was sold, in which territory, and how are sales trending (daily, weekly, monthly, yearly)?
- What is the status of orders? What are the income and expenses?

This backend reads the 1C database, adds its own agent/supervisor data, pre-computes the heavy aggregates in the background and serves everything through one authenticated JSON API for the dashboard frontend.

## How it works

`main.py` starts one FastAPI application that mounts two sub-applications:

| Mount | Package | Purpose |
|-------|---------|---------|
| `/agents` | `agents/` | Agent and supervisor management. Uses its own database (`AGENTS_DATABASE_URL`, migrated with Alembic) and reads 1C data (`ONEC_DATABASE_URL`). Has `/agents/health`. |
| `/` | `supervisor/` | Supervisor dashboard API: auth, employees, territories, agents, clients, orders, products, income/expense. Reads the 1C database. |

Both follow the same layering:

```
endpoints (routes)  ->  schemas (pydantic)  ->  repositories (SQL)  ->  models (SQLAlchemy)
```

Main route groups of the `supervisor` app: `/auth`, `/employee`, `/territory`, `/agent`, `/client`, `/order`, `/product`, `/income-expense`. All except `/auth` require a logged-in supervisor (JWT bearer token).

**Background jobs.** Some aggregates (sales growth, agent stats) are too expensive to compute per request. Celery workers recompute them on a schedule and store them in Redis, so requests only read the cached value:

- sales growth, daily/weekly/monthly: every 20 min
- sales growth, yearly: daily at 02:00 UTC
- agent stats: every 20 min

The API still works if Redis is down. The cache refresh fails fast instead of slowing down the request.

## Technologies

| Tool | Version | Role |
|------|---------|------|
| Python | 3.12 | Language |
| FastAPI | 0.139.0 | Web framework |
| Uvicorn | 0.50.0 | ASGI server |
| Pydantic | 2.13.4 | Request/response validation |
| pydantic-settings | 2.14.2 | Settings for the `agents` app |
| SQLAlchemy (async) | 2.0.51 | ORM |
| asyncpg | 0.31.0 | PostgreSQL driver |
| Alembic | 1.20.1 | Migrations for the agents database |
| PostgreSQL | any recent version | 1C data and agents data |
| Celery | 5.6.3 | Scheduled background jobs |
| Redis | server any recent version, client 6.4.0 | Celery broker and cache |
| PyJWT | 1.4.0 (`jwt`) | Authentication tokens |
| uv | latest | Dependency manager |
| Docker | any recent version | Deployment |
| pytest, pytest-asyncio, httpx | 9.1.1 / 1.4.0 / 0.28.1 | Tests (not in repo) |

Exact versions are pinned in `uv.lock`.

## Run it

### 1. Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL with the 1C database and an agents database
- Redis (only needed for the cache and background jobs)

### 2. Install

```bash
uv sync
```

### 3. Configure

Copy the example file and fill in real values:

```bash
cp .env.example .env
```

| Variable | Meaning |
|----------|---------|
| `HOST`, `PORT` | Address the server listens on (default `localhost:8000`) |
| `DATABASE_URL` | 1C database, `postgresql+asyncpg://user:password@host:5432/db` |
| `AGENTS_DATABASE_URL` | Agents database |
| `ONEC_DATABASE_URL` | 1C database for the agents app |
| `JWT_SECRET_KEY` | Secret for signing tokens. Required. Use a long random value |
| `ALLOWED_ORIGINS` | CORS origins for `/agents`, comma-separated (`*` for all) |
| `REDIS_URL` | Optional. Defaults to `redis://localhost:6379/0` |
| `DOCS_URL`, `OPENAPI_URL`, `REDOC_URL` | Optional. Paths for Swagger/OpenAPI docs of the supervisor app |

### 4. Migrate the agents database

```bash
uv run alembic -c agents/alembic.ini upgrade head
```

### 5. Start the API

```bash
uv run python main.py
```

The API is now at `http://localhost:8000`. The agents app is at `http://localhost:8000/agents`.

### 6. Start background jobs (optional)

Run these in two separate terminals:

```bash
uv run celery -A supervisor.src.core.celery_app worker --loglevel=info
uv run celery -A supervisor.src.core.celery_app beat --loglevel=info
```

### Docker

```bash
docker build -t supervisor-backend .
docker run -p 8000:8000 --env-file .env supervisor-backend
```

The container runs `uvicorn main:app` on port 8000 as a non-root user.

## Deployment

Pushing to `main` triggers `.github/workflows/deploy.yml`. It connects to the server over SSH, pulls the code and rebuilds the `supervisor_backend` container with Docker Compose. It needs the repository secrets `SERVER_IP` and `SERVER_PASSWORD`.

## Project layout

```
main.py            entry point, mounts both apps
supervisor/        dashboard API
  src/             core, endpoints, models, repositories, schemas, tasks
agents/            agent/supervisor management app
  src/             endpoints, services, repositories
  onec/            read access to the 1C database
  migrations/      Alembic migrations
Dockerfile         production image
```
