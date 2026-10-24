import pytest

from supervisor.tests.data import OLD_DATE, NEW_DATETIME


@pytest.mark.asyncio
async def test_get_all_territories_base(client, auth_headers):
    """GET /territory/all - base case, no optional params."""
    response = await client.get("/territory/all", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_all_territories_order_by_revenue(client, auth_headers):
    """GET /territory/all - optional order_by=revenue."""
    response = await client.get(
        "/territory/all", params={"order_by": "revenue"}, headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_all_territories_order_by_profit(client, auth_headers):
    """GET /territory/all - optional order_by=profit."""
    response = await client.get(
        "/territory/all", params={"order_by": "profit"}, headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_all_territories_date_range(client, auth_headers):
    """GET /territory/all - optional from_time/to_time set to a wide real range (requires order_by)."""
    response = await client.get(
        "/territory/all",
        params={"order_by": "revenue", "from_time": OLD_DATE, "to_time": NEW_DATETIME},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_all_territories_page(client, auth_headers):
    """GET /territory/all - optional page=2."""
    response = await client.get("/territory/all", params={"page": 2}, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_all_territories_limit(client, auth_headers):
    """GET /territory/all - optional limit=5."""
    response = await client.get("/territory/all", params={"limit": 5}, headers=auth_headers)
    assert response.status_code == 200
