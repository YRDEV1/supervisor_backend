import datetime

from fastapi import APIRouter, Depends
from typing import List

from app.src.repositories.client import ClientRepository
from app.src.schemas.client import ClientResponse, ClientType, ClientDetailResponse
from app.src.repositories.visit import VisitRepository
from app.src.core.auth import require_supervisor

client_router = APIRouter(tags=["Client details"], prefix="/client", dependencies=[Depends(require_supervisor)])

@client_router.get("/by-territory", summary="Get clients by territory")
async def get_clients_by_territory(territory_id: str, page: int = 1, limit: int = 25,
                                    client_repo: ClientRepository = Depends()) -> List[ClientResponse]:
    return await client_repo.get_by_territory(territory_id=bytes.fromhex(territory_id), page=page, limit=limit)

@client_router.get("/all", summary="Get all clients")
async def get_all_clients(search: str | None = None, type: ClientType = ClientType.OKB, page: int = 1, limit: int = 25,
                           client_repo: ClientRepository = Depends()) -> List[ClientResponse]:
    return await client_repo.get_all(client_type=type, page=page, limit=limit, search=search)

# @client_router.get("/by-agent", summary="Get clients by agent")
# async def get_clients_by_agent(agent_id: str, page: int = 1, limit: int = 25,
#                                 client_repo: ClientRepository = Depends()) -> List[ClientResponse]:
#     return await client_repo.get_by_agent(agent_id=bytes.fromhex(agent_id), page=page, limit=limit)

@client_router.get("/info", summary="Get client by id")
async def get_client_info(client_id: str, client_repo: ClientRepository = Depends()) -> ClientDetailResponse:
    return await client_repo.get_by_id(client_id=bytes.fromhex(client_id))

@client_router.get("/not-visited", summary="Get clients not visited on a given date, scoped to a supervisor's agents")
async def get_clients_not_visited(date: datetime.date, supervisor_id: str, page: int = 1, limit: int = 25,
                                   visit_repo: VisitRepository = Depends()) -> List[ClientResponse]:
    return await visit_repo.get_clients_not_visited_on_date(date=date, supervisor_id=bytes.fromhex(supervisor_id),
                                                              page=page, limit=limit)
