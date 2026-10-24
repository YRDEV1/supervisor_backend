import pytest

from supervisor.tests.data import OLD_DATE, NEW_DATETIME, ORDER_ID, assert_keyset_page


@pytest.mark.asyncio
async def test_get_all_orders_base(client, auth_headers):
    """GET /order/all - required params only, wide date range (default sort=newest_first)."""
    response = await client.get(
        "/order/all",
        params={"from_date": OLD_DATE, "to_date": NEW_DATETIME},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert_keyset_page(response.json())


@pytest.mark.asyncio
async def test_get_all_orders_status(client, auth_headers):
    """GET /order/all - optional status set to the dominant real status label."""
    response = await client.get(
        "/order/all",
        params={
            "from_date": OLD_DATE,
            "to_date": NEW_DATETIME,
            "status": "Доставлено",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_all_orders_sort_direction_oldest_first(client, auth_headers):
    """GET /order/all - optional sort_direction=oldest_first (non-default)."""
    response = await client.get(
        "/order/all",
        params={
            "from_date": OLD_DATE,
            "to_date": NEW_DATETIME,
            "sort_direction": "oldest_first",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_all_orders_cursor(client, auth_headers):
    """GET /order/all - second keyset page must not repeat the first."""
    params = {"from_date": OLD_DATE, "to_date": NEW_DATETIME, "limit": 5}
    first = await client.get("/order/all", params=params, headers=auth_headers)
    assert first.status_code == 200
    first_items = assert_keyset_page(first.json())
    cursor = first.json()["next_cursor"]
    if cursor is None:
        pytest.skip("only one page of orders in range")

    second = await client.get("/order/all", params={**params, "cursor": cursor}, headers=auth_headers)
    assert second.status_code == 200
    second_items = assert_keyset_page(second.json())
    assert not ({o["order_id"] for o in first_items} & {o["order_id"] for o in second_items})


@pytest.mark.asyncio
async def test_get_all_orders_bad_cursor(client, auth_headers):
    """GET /order/all - a malformed cursor is rejected, not silently ignored."""
    response = await client.get(
        "/order/all",
        params={"from_date": OLD_DATE, "to_date": NEW_DATETIME, "cursor": "not-a-cursor"},
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_all_orders_limit(client, auth_headers):
    """GET /order/all - optional limit=5."""
    response = await client.get(
        "/order/all",
        params={"from_date": OLD_DATE, "to_date": NEW_DATETIME, "limit": 5},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_order_statuses(client, auth_headers):
    """GET /order/statuses - no params."""
    response = await client.get("/order/statuses", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_order_info(client, auth_headers):
    """GET /order/info - required order_id, real value."""
    response = await client.get("/order/info", params={"order_id": ORDER_ID}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["order_id"] == ORDER_ID
