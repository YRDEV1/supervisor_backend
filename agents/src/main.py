from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.onec.database import onec_engine
from agents.src.core.config import settings
from agents.src.core.database import engine
from agents.src.endpoints.agent import agent_router
from agents.src.endpoints.supervisor import supervisor_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()
    await onec_engine.dispose()


app = FastAPI(title="Supervisor Agent Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)
app.include_router(supervisor_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
