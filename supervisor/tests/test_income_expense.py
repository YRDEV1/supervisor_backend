import pytest

from supervisor.tests.data import OLD_DATE, NEW_DATETIME, EMPLOYEE_ID, BRANCH_ID

pytestmark = pytest.mark.skip(reason="GET /income-expense/all is commented out for now")


@pytest.mark.asyncio
async def test_get_income_expense_base(client, auth_headers):
    """GET /income-expense/all - required from_date/to_date/employee_id, wide date range."""
    response = await client.get(
        "/income-expense/all",
        params={"from_date": OLD_DATE, "to_date": NEW_DATETIME, "employee_id": EMPLOYEE_ID},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_income_expense_with_branch_id(client, auth_headers):
    """GET /income-expense/all - optional branch_id set to a real value."""
    response = await client.get(
        "/income-expense/all",
        params={
            "from_date": OLD_DATE,
            "to_date": NEW_DATETIME,
            "employee_id": EMPLOYEE_ID,
            "branch_id": BRANCH_ID,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
