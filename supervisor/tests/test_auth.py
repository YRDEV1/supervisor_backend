import pytest

from supervisor.tests.data import SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD


@pytest.mark.asyncio
async def test_login_valid_credentials(client):
    """POST /auth/login - real supervisor login/password returns a token pair."""
    response = await client.post(
        "/auth/login", json={"login": SUPERVISOR_LOGIN, "password": SUPERVISOR_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_valid_token(client, auth_headers):
    """POST /auth/refresh - exchange a real refresh token for a new pair."""
    login_response = await client.post(
        "/auth/login", json={"login": SUPERVISOR_LOGIN, "password": SUPERVISOR_PASSWORD}
    )
    refresh_token = login_response.json()["refresh_token"]

    response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] and body["refresh_token"]
