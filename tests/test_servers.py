from fastapi.testclient import TestClient

from tests.utils import dict_without_key

from metaserver import config


def test_server_registration(client: TestClient, user: dict):
    server_create = dict(
        host_name="https://example.com",
        port=11235,
        display_name="Zaitev's Snooze Server",
        description="Welcome, grab a pillow.",
        game_type="RTSS",
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

    # OK: IPv4 host name
    resp = client.post(
        "/v1/server/register",
        json=server_create | {"host_name": "118.62.243.19"},
        auth=user["auth"],
    )
    assert resp.status_code == 200

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

    server_update = {
        "host_name": "10.0.0.67",
        "port": 11235,
        "display_name": "^mUnnamed ^900DRX ^mServer",
        "description": "This is a server that you can play on.",
        "game_type": "RTSS",
        "max_player_count": 32,
        "current_player_count": 1,
        "current_map": "eden2",
    }

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


def test_server_verify_clan_membership(
    client: TestClient,
    user: dict,
    user2: dict,
    clan_icon: str,
    server: dict,
):

    # Create a clan
    clan_name, clan_tag = "Zaitev's Snore Club", "Zzz"
    clan = client.post(
        "/v1/clan/register",
        json=dict(tag=clan_tag, name=clan_name, icon=clan_icon),
        auth=user["auth"],
    ).json()

    response = client.get(
        "/v1/clan/by-id",
        params=dict(clan_id=clan["id"]),
        auth=server["auth"],
    )

    assert response.status_code == 200
    assert response.json()["tag"] == clan["tag"]

    # Check that user is in clan
    response = client.post(
        "/v1/server/verify-clan-membership",
        json=dict(user_id=user["id"], clan_id=clan["id"]),
        auth=server["auth"],
    )
    assert response.json() is True

    # Check that user2 is not in clan
    response = client.post(
        "/v1/server/verify-clan-membership",
        json=dict(user_id=user2["id"], clan_id=clan["id"]),
        auth=server["auth"],
    )
    assert response.json() is False


def test_match_update(client: TestClient, user: dict, user2: dict, server: dict):
    response = client.get(
        "/v1/user/stats",
        params=dict(user_id=user["id"], server_id=server["id"]),
        auth=user["auth"],
    )

    assert response.status_code == 404

    # Post a draw and see if the ratings are stable at the initial level.
    response = client.post(
        "/v1/server/match-update",
        json={
            "teams": [
                {
                    "id": 0,
                    "race": "beast",
                    "field_players": [{"user_id": user["id"]}],
                    "commander": 9,
                },
                {
                    "id": 1,
                    "race": "human",
                    "field_players": [{"user_id": user2["id"]}],
                    "commander": 9,
                },
            ],
            "winner": -1,
        },
        auth=server["auth"],
    )
    assert response.status_code == 200

    response = client.get(
        "/v1/user/stats",
        params=dict(user_id=user["id"], server_id=server["id"]),
        auth=user["auth"],
    )
    assert response.status_code == 200
    assert response.json()["skill_rating"] == config.initial_user_skill_rating

    response = client.get(
        "/v1/user/stats",
        params=dict(user_id=user2["id"], server_id=server["id"]),
        auth=user["auth"],
    )

    assert response.status_code == 200
    assert response.json()["skill_rating"] == config.initial_user_skill_rating

    # Post a win for user and see if the ratings went in the right direction
    response = client.post(
        "/v1/server/match-update",
        json={
            "teams": [
                {
                    "id": 0,
                    "race": "beast",
                    "field_players": [{"user_id": user["id"]}],
                    "commander": 9,
                },
                {
                    "id": 1,
                    "race": "human",
                    "field_players": [{"user_id": user2["id"]}],
                    "commander": 9,
                },
            ],
            "winner": 0,
        },
        auth=server["auth"],
    )
    assert response.status_code == 200

    response = client.get(
        "/v1/user/stats",
        params=dict(user_id=user["id"], server_id=server["id"]),
        auth=user["auth"],
    )
    assert response.status_code == 200
    assert response.json()["skill_rating"] > config.initial_user_skill_rating
    user_post_update = response.json()["skill_rating"]

    response = client.get(
        "/v1/user/stats",
        params=dict(user_id=user2["id"], server_id=server["id"]),
        auth=user["auth"],
    )
    assert response.status_code == 200
    assert response.json()["skill_rating"] < config.initial_user_skill_rating
    user2_post_update = response.json()["skill_rating"]

    # Post a draw and see if the ratings went in the right direction
    response = client.post(
        "/v1/server/match-update",
        json={
            "teams": [
                {
                    "id": 0,
                    "race": "beast",
                    "field_players": [{"user_id": user["id"]}],
                    "commander": 9,
                },
                {
                    "id": 1,
                    "race": "human",
                    "field_players": [{"user_id": user2["id"]}],
                    "commander": 9,
                },
            ],
            "winner": -1,
        },
        auth=server["auth"],
    )
    assert response.status_code == 200

    response = client.get(
        "/v1/user/stats",
        params=dict(user_id=user["id"], server_id=server["id"]),
        auth=user["auth"],
    )
    assert response.status_code == 200
    assert response.json()["skill_rating"] < user_post_update
    user_post_update = response.json()["skill_rating"]

    response = client.get(
        "/v1/user/stats",
        params=dict(user_id=user2["id"], server_id=server["id"]),
        auth=user["auth"],
    )
    assert response.status_code == 200
    assert response.json()["skill_rating"] > user2_post_update
    user2_post_update = response.json()["skill_rating"]

    # Post a loss for user and see if the ratings went in the right direction
    response = client.post(
        "/v1/server/match-update",
        json={
            "teams": [
                {
                    "id": 0,
                    "race": "beast",
                    "field_players": [{"user_id": user["id"]}, {"user_id": -1}],
                    "commander": -5,
                },
                {
                    "id": 1,
                    "race": "human",
                    "field_players": [{"user_id": user2["id"]}],
                    "commander": 9,
                },
            ],
            "winner": 1,
        },
        auth=server["auth"],
    )
    assert response.status_code == 200

    response = client.get(
        "/v1/user/stats",
        params=dict(user_id=user["id"], server_id=server["id"]),
        auth=user["auth"],
    )
    assert response.status_code == 200
    assert response.json()["skill_rating"] < user_post_update

    response = client.get(
        "/v1/user/stats",
        params=dict(user_id=user2["id"], server_id=server["id"]),
        auth=user["auth"],
    )
    assert response.status_code == 200
    assert response.json()["skill_rating"] > user2_post_update
