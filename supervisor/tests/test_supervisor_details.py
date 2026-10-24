import pytest

from supervisor.tests.data import AUTH_SUPERVISOR_ID, AGENT_ID


@pytest.mark.asyncio
async def test_get_supervisor_details(client, auth_headers):
    """GET /employee/supervisors/info - no params, derives supervisor from the auth token."""
    response = await client.get("/employee/supervisors/info", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == AUTH_SUPERVISOR_ID


@pytest.mark.asyncio
async def test_get_supervisor_agents(client, auth_headers):
    """GET /employee/supervisors/agents - supervisor comes from the token."""
    response = await client.get("/employee/supervisors/agents", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_supervisor_agents_rejects_bad_page(client, auth_headers):
    """GET /employee/supervisors/agents - page below 1 is a validation error."""
    response = await client.get("/employee/supervisors/agents", params={"page": 0}, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_agent_info(client, auth_headers):
    """GET /employee/supervisors/agents/info - required agent_id, real value."""
    response = await client.get(
        "/employee/supervisors/agents/info", params={"agent_id": AGENT_ID}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["id"] == AGENT_ID
