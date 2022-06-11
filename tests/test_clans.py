from fastapi.testclient import TestClient


def test_clan_registration(client: TestClient):
    # Register a new user.
    username, password = "foo@example.com", "12345678"
    response = client.post(
        "/v1/user/register",
        json=dict(username=username, display_name="Zaitev", password=password),
    )
    assert response.status_code == 200

    # Register a new clan.
    clan_name, clan_tag = "Zaitev's Snore Club", "Zzz"
    response = client.post(
        "/v1/clan/register",
        json=dict(tag=clan_tag, name=clan_name),
        auth=(username, password),
    )
    assert response.status_code == 200
    assert response.json()["name"] == clan_name
    clan = response.json()

    # Get clan info
    response = client.get(
        "/v1/clan/by-id",
        json=dict(clan_id=clan["id"]),
        auth=(username, password),
    )
    assert clan == response.json()

    # Get clan members
    response = client.get(
        "/v1/clan/members",
        json=dict(clan_id=clan["id"]),
        auth=(username, password),
    )
    assert response.json()[0]["display_name"] == "Zaitev"

    # Register a new clan with an illegal name.
    response = client.post(
        "/v1/clan/register",
        json=dict(tag="^900" * 5, name="Zaitev's Snore Club"),
        auth=(username, password),
    )
    assert response.status_code == 422


def test_clan_invitation(client: TestClient):
    # Setup
    admin_auth = "foo@example.com", "12345678"
    clan_name, clan_tag = "Zaitev's Snore Club", "Zzz"
    nonadmin_auth = "bar@example.com", "10293801293"

    admin = client.post(
        "/v1/user/register",
        json=dict(
            username=admin_auth[0], display_name="Zaitev", password=admin_auth[1]
        ),
    ).json()
    nonadmin = client.post(
        "/v1/user/register",
        json=dict(
            username=nonadmin_auth[0], display_name="Hax", password=nonadmin_auth[1]
        ),
    ).json()
    clan = client.post(
        "/v1/clan/register", json=dict(tag=clan_tag, name=clan_name), auth=admin_auth
    ).json()

    # Outsider can't invite people.
    response = client.post(
        "/v1/clan/invite",
        json=dict(user_id=nonadmin["id"], clan_id=clan["id"]),
        auth=nonadmin_auth,
    )
    assert response.status_code == 401

    # Non-existent invite can't be accepted.
    response = client.post(
        "/v1/clan/accept-invite",
        json=dict(clan_id=clan["id"]),
        auth=nonadmin_auth,
    )
    assert response.status_code == 401

    # There are (still) no invites.
    response = client.get(
        "/v1/clan/invites",
        json=dict(clan_id=clan["id"]),
        auth=admin_auth,
    )
    assert response.json() == []

    # Admin is the only member.
    response = client.get(
        "/v1/clan/members",
        json=dict(clan_id=clan["id"]),
        auth=nonadmin_auth,
    )
    assert response.json() == [admin]

    # Admin can invite people.
    response = client.post(
        "/v1/clan/invite",
        json=dict(user_id=nonadmin["id"], clan_id=clan["id"]),
        auth=admin_auth,
    )
    assert response.status_code == 200

    # Invites go through and can be viewed.
    response = client.get(
        "/v1/clan/invites",
        json=dict(clan_id=clan["id"]),
        auth=admin_auth,
    )
    assert [inv["user_id"] for inv in response.json()] == [nonadmin["id"]]

    # Invites can be accepted.
    response = client.post(
        "/v1/clan/accept-invite",
        json=dict(clan_id=clan["id"]),
        auth=nonadmin_auth,
    )
    assert response.status_code == 200

    # Both admin and non-admin are now members.
    response = client.get(
        "/v1/clan/members",
        json=dict(clan_id=clan["id"]),
        auth=nonadmin_auth,
    )
    assert sorted(response.json(), key=lambda u: u["id"]) == sorted(
        [admin, nonadmin], key=lambda u: u["id"]
    )

    # Regular member can't invite people.
    response = client.post(
        "/v1/clan/invite",
        json=dict(user_id=nonadmin["id"], clan_id=clan["id"]),
        auth=nonadmin_auth,
    )
    assert response.status_code == 401
