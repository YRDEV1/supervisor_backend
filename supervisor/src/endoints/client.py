import datetime

from fastapi import APIRouter, Depends

from supervisor.src.repositories.client import ClientRepository
from supervisor.src.schemas.client import ClientResponse, ClientType, ClientDetailResponse, ClientPageResponse
from supervisor.src.repositories.visit import VisitRepository
from supervisor.src.repositories.employee import EmployeeRepository
from supervisor.src.core.auth import require_supervisor, CurrentUser
from supervisor.src.core.cursor import decode_decimal_id_cursor, encode_cursor
from supervisor.src.core.types import TASHKENT_TZ

client_router = APIRouter(tags=["Client details"], prefix="/client", dependencies=[Depends(require_supervisor)])

def _client_page(rows, has_more: bool) -> ClientPageResponse:
    return ClientPageResponse(
        items=[ClientResponse.model_validate(row) for row in rows],
        next_cursor=encode_cursor(rows[-1].code, rows[-1].id) if has_more and rows else None,
    )

@client_router.get("/by-territory", summary="Get clients by territory (keyset paginated)")
async def get_clients_by_territory(territory_id: str, cursor: str | None = None, limit: int = 25,
                                    client_repo: ClientRepository = Depends()) -> ClientPageResponse:
    rows, has_more = await client_repo.get_by_territory(
        territory_id=bytes.fromhex(territory_id), limit=limit,
        cursor=decode_decimal_id_cursor(cursor) if cursor else None)
    return _client_page(rows, has_more)

@client_router.get("/all", summary="Get all clients (keyset paginated)")
async def get_all_clients(search: str | None = None, type: ClientType = ClientType.OKB,
                           cursor: str | None = None, limit: int = 25,
                           client_repo: ClientRepository = Depends()) -> ClientPageResponse:
    rows, has_more = await client_repo.get_all(
        client_type=type, limit=limit, search=search,
        cursor=decode_decimal_id_cursor(cursor) if cursor else None)
    return _client_page(rows, has_more)

# @client_router.get("/by-agent", summary="Get clients by agent")
# async def get_clients_by_agent(agent_id: str, page: int = 1, limit: int = 25,
#                                 client_repo: ClientRepository = Depends()) -> List[ClientResponse]:
#     return await client_repo.get_by_agent(agent_id=bytes.fromhex(agent_id), page=page, limit=limit)

@client_router.get("/info", summary="Get client by id")
async def get_client_info(client_id: str, client_repo: ClientRepository = Depends()) -> ClientDetailResponse:
    return await client_repo.get_by_id(client_id=bytes.fromhex(client_id))

@client_router.get("/not-visited", summary="Get clients not visited on a given date, scoped to a supervisor's agents")
async def get_clients_not_visited(date: datetime.date | None, cursor: str | None = None, limit: int = 25,
                                   current_user: CurrentUser = Depends(require_supervisor),
                                   employee_repo: EmployeeRepository = Depends(),
                                   visit_repo: VisitRepository = Depends()) -> ClientPageResponse:
    date = datetime.datetime.now(TASHKENT_TZ).date() if date is None else date

    agent_ids = await employee_repo.get_supervisor_agent_ids(current_user.id)
    rows, has_more = await visit_repo.get_clients_not_visited_on_date(
        date=date, agent_ids=agent_ids, limit=limit,
        cursor=decode_decimal_id_cursor(cursor) if cursor else None)
    return _client_page(rows, has_more)
