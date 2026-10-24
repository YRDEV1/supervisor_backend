"""Real sample IDs used as fixtures across the test suite. `OLD_DATE` /
`NEW_DATETIME` bracket almost the entire orders table (-> 2026-06-12, the
newest record in both environments) so date-ranged endpoints return
non-empty results.

Set TEST_ENV=prod (see conftest.py / API_BASE_URL) to point the suite at
production instead of the in-process local app; the IDs below are swapped
to match, since local and production are different databases.
"""

import os

TEST_ENV = os.environ.get("TEST_ENV", "local")

OLD_DATE = "2020-01-01T00:00:00"
NEW_DATETIME = "2026-06-12T23:59:59"
NEW_DATE_ONLY = "2026-06-12"

INVALID_HEX_ID = "00" * 16

if TEST_ENV == "prod":
    SUPERVISOR_ID = "a73a005056070e0911f04f19c8691978"
    SUPERVISOR_LOGIN = "Отаёр"
    SUPERVISOR_PASSWORD = "8882"
    # The id behind SUPERVISOR_LOGIN/PASSWORD - same person as SUPERVISOR_ID here.
    AUTH_SUPERVISOR_ID = SUPERVISOR_ID

    AGENT_ID = "b511f0d4155608d711f084a403fd868c"
    TERRITORY_ID = "8046cc7bb6606cf611f092d230e05f02"
    CLIENT_ID = "a738005056070e0911f03a0da750907f"
    BRANCH_ID = "9cf1c32162bcc65e11eeb6b68a66468b"
    CATEGORY_ID = "8059a3e1875d42a811f14df1c2626572"
    ORDER_ID = "8059a3e1875d42a811f166615088c94b"
    EMPLOYEE_ID = SUPERVISOR_ID  # has real income/expense records in prod
else:
    SUPERVISOR_ID = "a738005056070e0911f03797035f4335"
    SUPERVISOR_LOGIN = "7002"
    SUPERVISOR_PASSWORD = "7002"
    # The id behind SUPERVISOR_LOGIN/PASSWORD - a different person from
    # SUPERVISOR_ID above (which is just used as an arbitrary filter value
    # for endpoints that take a supervisor_id param unrelated to auth).
    AUTH_SUPERVISOR_ID = "a738005056070e0911f036403e4c9d2a"

    AGENT_ID = "a738005056070e0911f0363cfdece78d"
    TERRITORY_ID = "a738005056070e0911f04b2651f32521"
    CLIENT_ID = "a738005056070e0911f04b2c4042d3af"
    BRANCH_ID = "8046cc7bb6606cf611f08a502a89b691"
    CATEGORY_ID = "b512f0d4155608d711f08be02b569d91"
    ORDER_ID = "8059a3e1875d42a811f166615088c94b"
    EMPLOYEE_ID = AGENT_ID


def assert_keyset_page(payload):
    """Assert a keyset-paginated envelope and return its items.

    Keyset endpoints answer with `{"items": [...], "next_cursor": str | None}`
    instead of a bare list; `next_cursor` is null on the final page.
    """
    assert isinstance(payload, dict), f"expected a keyset envelope, got {type(payload).__name__}"
    assert isinstance(payload.get("items"), list), payload
    assert "next_cursor" in payload, payload
    assert payload["next_cursor"] is None or isinstance(payload["next_cursor"], str), payload
    return payload["items"]
