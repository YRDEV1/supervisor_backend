from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from supervisor.src.core.config import DOCS_URL, OPENAPI_URL, REDOC_URL
from supervisor.src.core.database import warm_pool
from supervisor.src.endoints.auth import auth_router
from supervisor.src.endoints.employee import employee_router
from supervisor.src.endoints.territory import territory_router
from supervisor.src.endoints.income_expense import income_expense_router
from supervisor.src.endoints.agent_territory import agent_territory_router
from supervisor.src.endoints.client import client_router
from supervisor.src.endoints.order import order_router
from supervisor.src.endoints.product import product_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await warm_pool()
    yield

#app = FastAPI(docs_url=DOCS_URL, openapi_url=OPENAPI_URL, redoc_url=REDOC_URL)
app = FastAPI(lifespan=lifespan)

# Compress responses over 1KB (large agent/order list payloads benefit most).
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=1)

app.include_router(auth_router)
app.include_router(employee_router)
app.include_router(territory_router)
app.include_router(income_expense_router)
app.include_router(agent_territory_router)
app.include_router(client_router)
app.include_router(order_router)
app.include_router(product_router)