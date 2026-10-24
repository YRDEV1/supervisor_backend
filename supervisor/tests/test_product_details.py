import pytest

from supervisor.tests.data import OLD_DATE, NEW_DATETIME, TERRITORY_ID, CLIENT_ID, CATEGORY_ID, assert_keyset_page


@pytest.mark.asyncio
async def test_get_categories_base(client, auth_headers):
    """GET /product/categories - base case, no optional params."""
    response = await client.get("/product/categories", headers=auth_headers)
    assert response.status_code == 200
    assert_keyset_page(response.json())


@pytest.mark.asyncio
async def test_get_categories_name(client, auth_headers):
    """GET /product/categories - optional name filter with a real substring."""
    response = await client.get("/product/categories", params={"name": "а"}, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_categories_cursor(client, auth_headers):
    """GET /product/categories - second keyset page must not repeat the first."""
    first = await client.get("/product/categories", params={"limit": 5}, headers=auth_headers)
    assert first.status_code == 200
    first_items = assert_keyset_page(first.json())
    cursor = first.json()["next_cursor"]
    if cursor is None:
        pytest.skip("only one page of categories")

    second = await client.get(
        "/product/categories", params={"limit": 5, "cursor": cursor}, headers=auth_headers
    )
    assert second.status_code == 200
    second_items = assert_keyset_page(second.json())
    assert not ({c["id"] for c in first_items} & {c["id"] for c in second_items})


@pytest.mark.asyncio
async def test_get_categories_limit(client, auth_headers):
    """GET /product/categories - optional limit=5."""
    response = await client.get("/product/categories", params={"limit": 5}, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_all_products_base(client, auth_headers):
    """GET /product/all - base case, no optional params."""
    response = await client.get("/product/all", headers=auth_headers)
    assert response.status_code == 200
    assert_keyset_page(response.json())


@pytest.mark.asyncio
async def test_get_all_products_category_id(client, auth_headers):
    """GET /product/all - optional category_id set to a real value."""
    response = await client.get(
        "/product/all", params={"category_id": CATEGORY_ID}, headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_all_products_cursor(client, auth_headers):
    """GET /product/all - second keyset page must not repeat the first."""
    first = await client.get("/product/all", params={"limit": 10}, headers=auth_headers)
    assert first.status_code == 200
    first_items = assert_keyset_page(first.json())
    cursor = first.json()["next_cursor"]
    if cursor is None:
        pytest.skip("only one page of products")

    second = await client.get(
        "/product/all", params={"limit": 10, "cursor": cursor}, headers=auth_headers
    )
    assert second.status_code == 200
    second_items = assert_keyset_page(second.json())
    assert not ({p["id"] for p in first_items} & {p["id"] for p in second_items})


@pytest.mark.asyncio
async def test_get_all_products_limit(client, auth_headers):
    """GET /product/all - optional limit=10."""
    response = await client.get("/product/all", params={"limit": 10}, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_sold_products_base(client, auth_headers):
    """GET /product/sold - required date range only, default status=most."""
    response = await client.get(
        "/product/sold",
        params={"from_date": OLD_DATE, "to_date": NEW_DATETIME},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert_keyset_page(response.json())


@pytest.mark.asyncio
async def test_get_sold_products_status_most(client, auth_headers):
    """GET /product/sold - optional status=most (explicit)."""
    response = await client.get(
        "/product/sold",
        params={"from_date": OLD_DATE, "to_date": NEW_DATETIME, "status": "most"},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_sold_products_status_least(client, auth_headers):
    """GET /product/sold - optional status=least (non-default)."""
    response = await client.get(
        "/product/sold",
        params={"from_date": OLD_DATE, "to_date": NEW_DATETIME, "status": "least"},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_sold_products_cursor(client, auth_headers):
    """GET /product/sold - second keyset page must not repeat the first."""
    params = {"from_date": OLD_DATE, "to_date": NEW_DATETIME, "limit": 5}
    first = await client.get("/product/sold", params=params, headers=auth_headers)
    assert first.status_code == 200
    first_items = first.json()["items"]
    cursor = first.json()["next_cursor"]
    if cursor is None:
        pytest.skip("only one page of sold products")

    second = await client.get("/product/sold", params={**params, "cursor": cursor}, headers=auth_headers)
    assert second.status_code == 200
    second_items = second.json()["items"]
    assert not ({i["id"] for i in first_items} & {i["id"] for i in second_items})


@pytest.mark.asyncio
async def test_get_sold_products_limit(client, auth_headers):
    """GET /product/sold - optional limit=5."""
    response = await client.get(
        "/product/sold",
        params={"from_date": OLD_DATE, "to_date": NEW_DATETIME, "limit": 5},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_sales_summary_base(client, auth_headers):
    """GET /product/sales-summary - no params, branch derived from the auth token."""
    response = await client.get("/product/sales-summary", headers=auth_headers)
    assert response.status_code == 200
    assert "total_revenue" in response.json()


@pytest.mark.asyncio
async def test_get_sales_summary_date_range(client, auth_headers):
    """GET /product/sales-summary - optional from_date/to_date set to a wide real range."""
    response = await client.get(
        "/product/sales-summary",
        params={"from_date": OLD_DATE, "to_date": NEW_DATETIME},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_sales_summary_cursor(client, auth_headers):
    """GET /product/sales-summary - second keyset page must not repeat the first."""
    params = {"limit": 5}
    first = await client.get("/product/sales-summary", params=params, headers=auth_headers)
    assert first.status_code == 200
    first_items = first.json()["products"]
    cursor = first.json()["next_cursor"]
    if cursor is None:
        pytest.skip("only one page of summary products")

    second = await client.get("/product/sales-summary", params={**params, "cursor": cursor}, headers=auth_headers)
    assert second.status_code == 200
    second_items = second.json()["products"]
    assert not ({i["id"] for i in first_items} & {i["id"] for i in second_items})


@pytest.mark.asyncio
async def test_get_sales_summary_limit(client, auth_headers):
    """GET /product/sales-summary - optional limit=5."""
    response = await client.get(
        "/product/sales-summary", params={"limit": 5}, headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_sales_summary_sort_by_quantity_sold(client, auth_headers):
    """GET /product/sales-summary - optional sort_by=quantity_sold."""
    response = await client.get(
        "/product/sales-summary",
        params={"sort_by": "quantity_sold"},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_sales_summary_sort_by_profit(client, auth_headers):
    """GET /product/sales-summary - optional sort_by=profit."""
    response = await client.get(
        "/product/sales-summary", params={"sort_by": "profit"}, headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_territory_stats_base(client, auth_headers):
    """GET /product/territory-stats - required territory_id only, optional times omitted."""
    response = await client.get(
        "/product/territory-stats", params={"territory_id": TERRITORY_ID}, headers=auth_headers
    )
    assert response.status_code == 200
    assert "total_revenue" in response.json()


@pytest.mark.asyncio
async def test_get_territory_stats_date_range(client, auth_headers):
    """GET /product/territory-stats - optional from_time/to_time set to a wide real range."""
    response = await client.get(
        "/product/territory-stats",
        params={"territory_id": TERRITORY_ID, "from_time": OLD_DATE, "to_time": NEW_DATETIME},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_territory_stats_cursor(client, auth_headers):
    """GET /product/territory-stats - second keyset page must not repeat the first."""
    params = {"territory_id": TERRITORY_ID, "limit": 5}
    first = await client.get("/product/territory-stats", params=params, headers=auth_headers)
    assert first.status_code == 200
    first_items = first.json()["products"]
    cursor = first.json()["next_cursor"]
    if cursor is None:
        pytest.skip("only one page of territory products")

    second = await client.get("/product/territory-stats", params={**params, "cursor": cursor}, headers=auth_headers)
    assert second.status_code == 200
    second_items = second.json()["products"]
    assert not ({i["id"] for i in first_items} & {i["id"] for i in second_items})


@pytest.mark.asyncio
async def test_get_territory_stats_limit(client, auth_headers):
    """GET /product/territory-stats - optional limit=5."""
    response = await client.get(
        "/product/territory-stats",
        params={"territory_id": TERRITORY_ID, "limit": 5},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_territory_stats_sort_by_quantity_sold(client, auth_headers):
    """GET /product/territory-stats - optional sort_by=quantity_sold."""
    response = await client.get(
        "/product/territory-stats",
        params={"territory_id": TERRITORY_ID, "sort_by": "quantity_sold"},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_territory_stats_sort_by_profit(client, auth_headers):
    """GET /product/territory-stats - optional sort_by=profit."""
    response = await client.get(
        "/product/territory-stats",
        params={"territory_id": TERRITORY_ID, "sort_by": "profit"},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_sales_growth_base(client, auth_headers):
    """GET /product/sales-growth - base case, reference_date omitted (defaults to now)."""
    response = await client.get("/product/sales-growth", headers=auth_headers)
    assert response.status_code == 200
    assert "daily" in response.json()


@pytest.mark.asyncio
async def test_get_sales_growth_reference_date(client, auth_headers):
    """GET /product/sales-growth - optional reference_date set to the newest real order date."""
    response = await client.get(
        "/product/sales-growth", params={"reference_date": NEW_DATETIME}, headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_branch_plan_base(client, auth_headers):
    """GET /product/branch-plan - base case, reference_date omitted (defaults to current month)."""
    response = await client.get("/product/branch-plan", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "total_plan" in body
    assert isinstance(body["agents"], list)
    assert sum(float(a["plan_amount"]) for a in body["agents"]) == float(body["total_plan"])


@pytest.mark.asyncio
async def test_get_branch_plan_reference_date(client, auth_headers):
    """GET /product/branch-plan - optional reference_date set to the newest real order date."""
    response = await client.get(
        "/product/branch-plan", params={"reference_date": NEW_DATETIME}, headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_client_stats_base(client, auth_headers):
    """GET /product/client-stats - required client_id only, optional times omitted."""
    response = await client.get(
        "/product/client-stats", params={"client_id": CLIENT_ID}, headers=auth_headers
    )
    assert response.status_code == 200
    assert "total_revenue" in response.json()


@pytest.mark.asyncio
async def test_get_client_stats_date_range(client, auth_headers):
    """GET /product/client-stats - optional from_time/to_time set to a wide real range."""
    response = await client.get(
        "/product/client-stats",
        params={"client_id": CLIENT_ID, "from_time": OLD_DATE, "to_time": NEW_DATETIME},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_client_stats_cursor(client, auth_headers):
    """GET /product/client-stats - second keyset page must not repeat the first."""
    params = {"client_id": CLIENT_ID, "limit": 5}
    first = await client.get("/product/client-stats", params=params, headers=auth_headers)
    assert first.status_code == 200
    first_items = first.json()["products"]
    cursor = first.json()["next_cursor"]
    if cursor is None:
        pytest.skip("only one page of client products")

    second = await client.get("/product/client-stats", params={**params, "cursor": cursor}, headers=auth_headers)
    assert second.status_code == 200
    second_items = second.json()["products"]
    assert not ({i["id"] for i in first_items} & {i["id"] for i in second_items})


@pytest.mark.asyncio
async def test_get_client_stats_limit(client, auth_headers):
    """GET /product/client-stats - optional limit=5."""
    response = await client.get(
        "/product/client-stats", params={"client_id": CLIENT_ID, "limit": 5}, headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_client_stats_sort_by_quantity_sold(client, auth_headers):
    """GET /product/client-stats - optional sort_by=quantity_sold."""
    response = await client.get(
        "/product/client-stats",
        params={"client_id": CLIENT_ID, "sort_by": "quantity_sold"},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_client_stats_sort_by_profit(client, auth_headers):
    """GET /product/client-stats - optional sort_by=profit."""
    response = await client.get(
        "/product/client-stats",
        params={"client_id": CLIENT_ID, "sort_by": "profit"},
        headers=auth_headers,
    )
    assert response.status_code == 200
