from fastapi import FastAPI

from app.src.core.config import DOCS_URL, OPENAPI_URL, REDOC_URL
from app.src.endoints.auth import auth_router
from app.src.endoints.employee import employee_router
from app.src.endoints.territory import territory_router
from app.src.endoints.income_expense import income_expense_router
from app.src.endoints.agent_territory import agent_territory_router
from app.src.endoints.client import client_router
from app.src.endoints.order import order_router
from app.src.endoints.product import product_router

#app = FastAPI(docs_url=DOCS_URL, openapi_url=OPENAPI_URL, redoc_url=REDOC_URL)
app = FastAPI()

app.include_router(auth_router)
app.include_router(employee_router)
app.include_router(territory_router)
app.include_router(income_expense_router)
app.include_router(agent_territory_router)
app.include_router(client_router)
app.include_router(order_router)
app.include_router(product_router)