import contextvars
import json
import os
import socket

os.environ["DOCS_URL"] = ""
os.environ["OPENAPI_URL"] = ""
os.environ["REDOC_URL"] = ""

# DNS pin for a specific host (e.g. when its DNS record is temporarily down
# but the server itself is reachable by IP). Only affects that one hostname;
# everything else resolves normally.
_DNS_PIN_HOST = os.environ.get("DNS_PIN_HOST")
_DNS_PIN_IP = os.environ.get("DNS_PIN_IP")
if _DNS_PIN_HOST and _DNS_PIN_IP:
    _orig_getaddrinfo = socket.getaddrinfo

    def _pinned_getaddrinfo(host, *args, **kwargs):
        if host == _DNS_PIN_HOST or (isinstance(host, bytes) and host == _DNS_PIN_HOST.encode()):
            host = _DNS_PIN_IP
        return _orig_getaddrinfo(host, *args, **kwargs)

    socket.getaddrinfo = _pinned_getaddrinfo

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from supervisor.tests.data import SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD

API_BASE_URL = os.environ.get("API_BASE_URL")
TEST_ENV = os.environ.get("TEST_ENV", "local")

_current_nodeid = contextvars.ContextVar("current_nodeid", default=None)
_captures: dict[str, list[dict]] = {}


async def _record_response(response):
    nodeid = _current_nodeid.get()
    if nodeid is None:
        return
    await response.aread()
    try:
        body = response.json()
    except Exception:
        body = response.text
    _captures.setdefault(nodeid, []).append({
        "method": response.request.method,
        "path": response.request.url.path,
        "url": str(response.request.url),
        "status_code": response.status_code,
        "body": body,
    })


@pytest.fixture(autouse=True)
def _tag_requests_with_nodeid(request):
    token = _current_nodeid.set(request.node.nodeid)
    yield
    _current_nodeid.reset(token)


def pytest_sessionfinish(session, exitstatus):
    out_path = os.path.join(os.path.dirname(__file__), "..", f"responses_{TEST_ENV}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(_captures, f, ensure_ascii=False, indent=2, default=str)


@pytest_asyncio.fixture(scope="session")
async def client():
    if API_BASE_URL:
        async with AsyncClient(
            base_url=API_BASE_URL, timeout=30, event_hooks={"response": [_record_response]}
        ) as ac:
            yield ac
        return

    from supervisor.src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", event_hooks={"response": [_record_response]}
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="session")
async def auth_headers(client: AsyncClient):
    response = await client.post(
        "/auth/login", json={"login": SUPERVISOR_LOGIN, "password": SUPERVISOR_PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
