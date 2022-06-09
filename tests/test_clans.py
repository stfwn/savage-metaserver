from fastapi.testclient import TestClient
import pytest

import metaserver


def test_clans(client: TestClient):
    # Register a new user.
    username, password = "foo@example.com", "12345678"
    response = client.post(
        "/v1/user/register",
        json={"username": username, "display_name": "Zaitev", "password": password},
    )
    assert response.status_code == 200

    # Register a new clan.
    clan_name = "Zaitev's Snore Club"
    response = client.post(
        "/v1/clan/register",
        json={"tag": "Zzz", "name": clan_name},
        auth=(username, password),
    )
    assert response.status_code == 200
    assert response.json()["name"] == clan_name

    # Get clan members
    response = client.get(
        "/v1/clan/members",
        params=dict(clan_tag="Zzz"),
        auth=(username, password),
    )
    assert response.json()[0]["display_name"] == "Zaitev"

    # Register a new clan with an illegal name.
    response = client.post(
        "/v1/clan/register",
        json={"tag": "^900" * 5, "name": "Zaitev's Snore Club"},
        auth=(username, password),
    )
    assert response.status_code == 422
