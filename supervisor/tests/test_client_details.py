import pytest

from supervisor.tests.data import TERRITORY_ID, CLIENT_ID, NEW_DATE_ONLY, assert_keyset_page


@pytest.mark.asyncio
async def test_get_clients_by_territory_base(client, auth_headers):
    """GET /client/by-territory - required territory_id, real value."""
    response = await client.get(
        "/client/by-territory", params={"territory_id": TERRITORY_ID}, headers=auth_headers
    )
    assert response.status_code == 200
    assert_keyset_page(response.json())


@pytest.mark.asyncio
async def test_get_clients_by_territory_cursor(client, auth_headers):
    """GET /client/by-territory - second keyset page must not repeat the first."""
    first = await client.get(
        "/client/by-territory",
        params={"territory_id": TERRITORY_ID, "limit": 5},
        headers=auth_headers,
    )
    assert first.status_code == 200
    first_items = assert_keyset_page(first.json())
    cursor = first.json()["next_cursor"]
    if cursor is None:
        pytest.skip("territory has only one page of clients")

    second = await client.get(
        "/client/by-territory",
        params={"territory_id": TERRITORY_ID, "limit": 5, "cursor": cursor},
        headers=auth_headers,
    )
    assert second.status_code == 200
    second_items = assert_keyset_page(second.json())
    assert not ({c["id"] for c in first_items} & {c["id"] for c in second_items})


@pytest.mark.asyncio
async def test_get_clients_by_territory_limit(client, auth_headers):
    """GET /client/by-territory - optional limit=5."""
    response = await client.get(
        "/client/by-territory",
        params={"territory_id": TERRITORY_ID, "limit": 5},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_all_clients_base(client, auth_headers):
    """GET /client/all - base case, no optional params (default type=OKB)."""
    response = await client.get("/client/all", headers=auth_headers)
    assert response.status_code == 200
    assert_keyset_page(response.json())


@pytest.mark.asyncio
async def test_get_all_clients_search(client, auth_headers):
    """GET /client/all - optional search set to a real substring."""
    response = await client.get("/client/all", params={"search": "а"}, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_all_clients_type_akb(client, auth_headers):
    """GET /client/all - optional type=AKB (non-default enum value)."""
    response = await client.get("/client/all", params={"type": "AKB"}, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_all_clients_page(client, auth_headers):
    """GET /client/all - second keyset page must not repeat the first."""
    first = await client.get("/client/all", params={"limit": 5}, headers=auth_headers)
    assert first.status_code == 200
    first_items = assert_keyset_page(first.json())
    cursor = first.json()["next_cursor"]
    if cursor is None:
        pytest.skip("only one page of clients")

    second = await client.get(
        "/client/all", params={"limit": 5, "cursor": cursor}, headers=auth_headers
    )
    assert second.status_code == 200
    second_items = assert_keyset_page(second.json())
    assert not ({c["id"] for c in first_items} & {c["id"] for c in second_items})


@pytest.mark.asyncio
async def test_get_all_clients_limit(client, auth_headers):
    """GET /client/all - optional limit=5."""
    response = await client.get("/client/all", params={"limit": 5}, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_client_info(client, auth_headers):
    """GET /client/info - required client_id, real value."""
    response = await client.get("/client/info", params={"client_id": CLIENT_ID}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == CLIENT_ID


@pytest.mark.asyncio
async def test_get_clients_not_visited_base(client, auth_headers):
    """GET /client/not-visited - required date only, supervisor derived from the auth token."""
    response = await client.get(
        "/client/not-visited",
        params={"date": NEW_DATE_ONLY},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert_keyset_page(response.json())


@pytest.mark.asyncio
async def test_get_clients_not_visited_cursor(client, auth_headers):
    """GET /client/not-visited - second keyset page must not repeat the first."""
    params = {"date": NEW_DATE_ONLY, "limit": 5}
    first = await client.get("/client/not-visited", params=params, headers=auth_headers)
    assert first.status_code == 200
    first_items = assert_keyset_page(first.json())
    cursor = first.json()["next_cursor"]
    if cursor is None:
        pytest.skip("only one page of not-visited clients")

    second = await client.get(
        "/client/not-visited", params={**params, "cursor": cursor}, headers=auth_headers
    )
    assert second.status_code == 200
    second_items = assert_keyset_page(second.json())
    assert not ({c["id"] for c in first_items} & {c["id"] for c in second_items})


@pytest.mark.asyncio
async def test_get_clients_not_visited_limit(client, auth_headers):
    """GET /client/not-visited - optional limit=5."""
    response = await client.get(
        "/client/not-visited",
        params={"date": NEW_DATE_ONLY, "limit": 5},
        headers=auth_headers,
    )
    assert response.status_code == 200
