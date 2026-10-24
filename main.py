from contextlib import asynccontextmanager

from fastapi import FastAPI
from uvicorn import run

from agents.src.main import app as agents_app
from supervisor.src.core.config import HOST, PORT
from supervisor.src.main import app as supervisor_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Mounted apps don't run their own startup
    async with agents_app.router.lifespan_context(agents_app):
        async with supervisor_app.router.lifespan_context(supervisor_app):
            yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

# Agents first, supervisor catches the rest
app.mount("/agents", agents_app)
app.mount("/", supervisor_app)

if __name__ == "__main__":
    run(app="main:app", host=HOST, port=PORT)
