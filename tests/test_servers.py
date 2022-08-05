from fastapi.testclient import TestClient

from tests.utils import dict_without_key

from metaserver import config


def test_server_registration(client: TestClient, user: dict):
    server_create = dict(
        host_name="https://example.com",
        display_name="Zaitev's Snooze Server",
        description="Welcome, grab a pillow.",
        game_type="Snoozing",
        max_player_count=42,
    )

    # Bad json
    resp = client.post(
        "/v1/server/register",
        json=dict(malformed=True),
        auth=user["auth"],
    )
    assert resp.status_code == 422

    # HTTP, not HTTPS
    resp = client.post(
        "/v1/server/register",
        json=server_create | {"host_name": "http://example.com"},
        auth=user["auth"],
    )
    assert resp.status_code == 422

    # OK
    resp = client.post(
        "/v1/server/register",
        json=server_create,
        auth=user["auth"],
    )

    assert resp.status_code == 200
    for k in ["username", "password"]:
        assert k in resp.json().keys()

    # Too many servers
    for _ in range(config.max_servers_per_user):
        resp = client.post(
            "/v1/server/register",
            json=server_create,
            auth=user["auth"],
        )
    assert resp.status_code == 400


def test_server_list_and_update(client: TestClient, user: dict, server: dict):
    resp = client.get("/v1/server/list/my", auth=user["auth"])
    assert resp.status_code == 200
    assert type(resp.json()) == list
    assert len(resp.json()) == 1

    resp = client.get("/v1/server/list/online", auth=user["auth"])
    assert resp.status_code == 200
    assert resp.json() == []

    server_update = dict(
        host_name="https://example2.com",
        display_name="Zaitev's updated snooze server",
        description="Grab an updated pillow.",
        game_type="Snoozing",
        current_player_count=40,
        max_player_count=42,
    )
    resp = client.post("/v1/server/update", json=server_update, auth=server["auth"])
    assert resp.status_code == 200

    new_server = resp.json()
    for k, v in server_update.items():
        assert new_server[k] == v

    new_server = client.get("/v1/server/list/my", auth=user["auth"]).json()[0]
    for k, v in server_update.items():
        assert new_server[k] == v

    resp = client.get("/v1/server/list/online", auth=user["auth"])
    assert resp.status_code == 200
    assert len(resp.json()) == 1
