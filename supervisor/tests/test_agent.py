import pytest

from supervisor.tests.data import AGENT_ID, CLIENT_ID, OLD_DATE, NEW_DATETIME, NEW_DATE_ONLY, assert_keyset_page


@pytest.mark.asyncio
async def test_get_agent_territories(client, auth_headers):
    """GET /agent/territories - required agent_id, real value."""
    response = await client.get(
        "/agent/territories", params={"agent_id": AGENT_ID}, headers=auth_headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_agent_visit_history_base(client, auth_headers):
    """GET /agent/visit-history - required params only, wide date range."""
    response = await client.get(
        "/agent/visit-history",
        params={"agent_id": AGENT_ID, "from_date": OLD_DATE, "to_date": NEW_DATETIME},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert_keyset_page(response.json())


@pytest.mark.asyncio
async def test_get_agent_visit_history_with_client_id(client, auth_headers):
    """GET /agent/visit-history - optional client_id set to a real value."""
    response = await client.get(
        "/agent/visit-history",
        params={
            "agent_id": AGENT_ID,
            "from_date": OLD_DATE,
            "to_date": NEW_DATETIME,
            "client_id": CLIENT_ID,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert_keyset_page(response.json())


@pytest.mark.asyncio
async def test_get_entry_count(client, auth_headers):
    """GET /agent/entry-count - all params required, wide date range."""
    response = await client.get(
        "/agent/entry-count",
        params={
            "agent_id": AGENT_ID,
            "client_id": CLIENT_ID,
            "from_time": OLD_DATE,
            "to_time": NEW_DATETIME,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "entry_count" in response.json()


@pytest.mark.asyncio
async def test_get_not_visited_clients_with_days(client, auth_headers):
    """GET /agent/not-visited-clients - base case using the `days` variant."""
    response = await client.get(
        "/agent/not-visited-clients",
        params={"agent_id": AGENT_ID, "days": 30},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert_keyset_page(response.json())


@pytest.mark.asyncio
async def test_get_not_visited_clients_with_custom_date(client, auth_headers):
    """GET /agent/not-visited-clients - alternate case using `custom_date` instead of `days`."""
    response = await client.get(
        "/agent/not-visited-clients",
        params={"agent_id": AGENT_ID, "custom_date": NEW_DATETIME},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert_keyset_page(response.json())


@pytest.mark.asyncio
async def test_get_not_visited_clients_cursor(client, auth_headers):
    """GET /agent/not-visited-clients - second keyset page must not repeat the first."""
    params = {"agent_id": AGENT_ID, "days": 30, "limit": 5}
    first = await client.get("/agent/not-visited-clients", params=params, headers=auth_headers)
    assert first.status_code == 200
    first_items = assert_keyset_page(first.json())
    cursor = first.json()["next_cursor"]
    if cursor is None:
        pytest.skip("only one page of not-visited clients")

    second = await client.get(
        "/agent/not-visited-clients", params={**params, "cursor": cursor}, headers=auth_headers
    )
    assert second.status_code == 200
    second_items = assert_keyset_page(second.json())
    assert not ({c["id"] for c in first_items} & {c["id"] for c in second_items})


@pytest.mark.asyncio
async def test_get_not_visited_clients_limit(client, auth_headers):
    """GET /agent/not-visited-clients - optional limit=5."""
    response = await client.get(
        "/agent/not-visited-clients",
        params={"agent_id": AGENT_ID, "days": 30, "limit": 5},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_agent_idle_time_base(client, auth_headers):
    """GET /agent/idle-time - required agent_id/date, default threshold_minutes."""
    response = await client.get(
        "/agent/idle-time",
        params={"agent_id": AGENT_ID, "date": NEW_DATE_ONLY},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_agent_idle_time_with_threshold(client, auth_headers):
    """GET /agent/idle-time - optional threshold_minutes=30."""
    response = await client.get(
        "/agent/idle-time",
        params={"agent_id": AGENT_ID, "date": NEW_DATE_ONLY, "threshold_minutes": 30},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_agent_stats_base(client, auth_headers):
    """GET /agent/stats - required agent_id, default top_products_limit."""
    response = await client.get(
        "/agent/stats", params={"agent_id": AGENT_ID}, headers=auth_headers
    )
    assert response.status_code == 200
    assert "order_count" in response.json()


@pytest.mark.asyncio
async def test_get_agent_stats_with_top_products_limit(client, auth_headers):
    """GET /agent/stats - optional top_products_limit=3."""
    response = await client.get(
        "/agent/stats",
        params={"agent_id": AGENT_ID, "top_products_limit": 3},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_agent_ratings_base(client, auth_headers):
    """GET /agent/ratings - required date range only, default sort_by=revenue."""
    response = await client.get(
        "/agent/ratings",
        params={"from_time": OLD_DATE, "to_time": NEW_DATETIME},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert_keyset_page(response.json())


@pytest.mark.asyncio
async def test_get_agent_ratings_cursor(client, auth_headers):
    """GET /agent/ratings - second keyset page must not repeat the first."""
    params = {"from_time": OLD_DATE, "to_time": NEW_DATETIME, "limit": 5}
    first = await client.get("/agent/ratings", params=params, headers=auth_headers)
    assert first.status_code == 200
    first_items = first.json()["items"]
    cursor = first.json()["next_cursor"]
    if cursor is None:
        pytest.skip("only one page of agent ratings")

    second = await client.get("/agent/ratings", params={**params, "cursor": cursor}, headers=auth_headers)
    assert second.status_code == 200
    second_items = second.json()["items"]
    assert not ({i["id"] for i in first_items} & {i["id"] for i in second_items})


@pytest.mark.asyncio
async def test_get_agent_ratings_limit(client, auth_headers):
    """GET /agent/ratings - optional limit=10."""
    response = await client.get(
        "/agent/ratings",
        params={"from_time": OLD_DATE, "to_time": NEW_DATETIME, "limit": 10},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_agent_ratings_sort_by_quantity_sold(client, auth_headers):
    """GET /agent/ratings - optional sort_by=quantity_sold."""
    response = await client.get(
        "/agent/ratings",
        params={"from_time": OLD_DATE, "to_time": NEW_DATETIME, "sort_by": "quantity_sold"},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_agent_ratings_sort_by_profit(client, auth_headers):
    """GET /agent/ratings - optional sort_by=profit."""
    response = await client.get(
        "/agent/ratings",
        params={"from_time": OLD_DATE, "to_time": NEW_DATETIME, "sort_by": "profit"},
        headers=auth_headers,
    )
    assert response.status_code == 200
