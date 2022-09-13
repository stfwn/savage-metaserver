from fastapi.testclient import TestClient

from tests.utils import dict_without_key, get_random_icon


def test_clan_registration(client: TestClient, user: dict, clan_icon: str):
    # Register a new clan.
    clan_name, clan_tag = "Zaitev's Snore Club", "^123(Zzz"
    response = client.post(
        "/v1/clan/register",
        json=dict(tag=clan_tag, name=clan_name, icon=clan_icon),
        auth=user["auth"],
    )
    assert response.status_code == 200
    assert response.json()["name"] == clan_name
    clan = response.json()

    # Get clan info
    response = client.get(
        "/v1/clan/by-id",
        params=dict(clan_id=clan["id"]),
        auth=user["auth"],
    )
    assert clan == response.json()

    # Get clan members
    response = client.get(
        "/v1/clan/members",
        params=dict(clan_id=clan["id"]),
        auth=user["auth"],
    )
    assert response.json()[0]["user_id"] == user["id"]

    # Register a new clan with an illegal name.
    response = client.post(
        "/v1/clan/register",
        json=dict(tag="^900" * 5, name="Zaitev's Snore Club", icon=clan_icon),
        auth=user["auth"],
    )
    assert response.status_code == 422

    # Get list of clans
    response = client.get(
        "/v1/clan/by-id/batch",
        params=dict(clan_ids=[1, 2]),
        auth=user["auth"],
    ).json()
    assert response[0] == clan
    assert len(response) == 1

    clan_tag2 = clan_tag[:-1] + "2"
    clan2 = dict(tag=clan_tag2, name=clan_name + "2", icon=clan_icon)
    response = client.post(
        "/v1/clan/register",
        json=clan2,
        auth=user["auth"],
    )

    response = client.get(
        "/v1/clan/by-id/batch",
        params=dict(clan_ids=[1, 2]),
        auth=user["auth"],
    ).json()
    assert len(response) == 2
    assert response[0] == clan
    assert response[1]["name"] == clan2["name"]


def test_clan_invitation(client: TestClient, user: dict, user2: dict, clan_icon: str):
    # Setup
    clan_name, clan_tag = "Zaitev's Snore Club", "Zzz"

    admin = dict_without_key(user, "proof")
    nonadmin = dict_without_key(user2, "proof")
    clan = client.post(
        "/v1/clan/register",
        json=dict(tag=clan_tag, name=clan_name, icon=clan_icon),
        auth=admin["auth"],
    ).json()

    # Outsider can't invite people.
    response = client.post(
        "/v1/clan/invite",
        json=dict(user_id=nonadmin["id"], clan_id=clan["id"]),
        auth=nonadmin["auth"],
    )
    assert response.status_code == 401

    # Non-existent invite can't be accepted.
    response = client.post(
        "/v1/clan/invite-response",
        json=dict(clan_id=clan["id"], accept=True),
        auth=nonadmin["auth"],
    )
    assert response.status_code == 422

    # There are (still) no invites.
    response = client.get(
        "/v1/clan/invites",
        params=dict(clan_id=clan["id"]),
        auth=admin["auth"],
    )
    assert response.json() == []

    # Admin is the only member.
    response = client.get(
        "/v1/clan/members",
        params=dict(clan_id=clan["id"]),
        auth=nonadmin["auth"],
    )
    assert [l["user_id"] for l in response.json()] == [admin["id"]]

    # Admin is a member
    response = client.post(
        "/v1/user/verify-clan-membership",
        json=dict(clan_id=clan["id"]),
        auth=admin["auth"],
    )
    assert response.json() == True

    # The list of clans for admin includes this clan
    response = client.get(
        "/v1/clan/for-user/by-id",
        params=dict(user_id=admin["id"]),
        auth=admin["auth"],
    )
    r = response.json()
    assert len(r) == 1
    assert r[0]["user_id"] == admin["id"]

    # Non-admin is not a member
    response = client.post(
        "/v1/user/verify-clan-membership",
        json=dict(clan_id=clan["id"]),
        auth=nonadmin["auth"],
    )
    assert response.json() == False

    # Admin can invite people.
    response = client.post(
        "/v1/clan/invite",
        json=dict(user_id=nonadmin["id"], clan_id=clan["id"]),
        auth=admin["auth"],
    )
    assert response.status_code == 200

    # Invites go through and can be viewed.
    response = client.get(
        "/v1/clan/invites",
        params=dict(clan_id=clan["id"]),
        auth=admin["auth"],
    )
    assert [inv["user_id"] for inv in response.json()] == [nonadmin["id"]]

    # Non-admin is still not a member
    response = client.post(
        "/v1/user/verify-clan-membership",
        json=dict(clan_id=clan["id"]),
        auth=nonadmin["auth"],
    )
    assert response.json() == False

    # Invites can be accepted.
    response = client.post(
        "/v1/clan/invite-response",
        json=dict(clan_id=clan["id"], accept=True),
        auth=nonadmin["auth"],
    )
    assert response.status_code == 200

    # Members cannot kick users
    response = client.post(
        "/v1/clan/kick",
        json=dict(user_id=admin["id"], clan_id=clan["id"]),
        auth=nonadmin["auth"],
    )
    assert response.status_code == 403

    # Both admin and non-admin are now members.
    response = client.get(
        "/v1/clan/members",
        params=dict(clan_id=clan["id"]),
        auth=nonadmin["auth"],
    )
    assert sorted([l["user_id"] for l in response.json()]) == sorted(
        [admin["id"], nonadmin["id"]]
    )

    # Regular member can't invite people.
    response = client.post(
        "/v1/clan/invite",
        json=dict(user_id=nonadmin["id"], clan_id=clan["id"]),
        auth=nonadmin["auth"],
    )
    assert response.status_code == 401

    # Admin can kick users
    response = client.post(
        "/v1/clan/kick",
        json=dict(user_id=nonadmin["id"], clan_id=clan["id"]),
        auth=admin["auth"],
    )
    assert response.status_code == 200
    response = client.post(
        "/v1/user/verify-clan-membership",
        json=dict(clan_id=clan["id"]),
        auth=nonadmin["auth"],
    )
    assert response.json() is False

    # Now only admin is a member
    response = client.get(
        "/v1/clan/members",
        params=dict(clan_id=clan["id"]),
        auth=nonadmin["auth"],
    )
    assert [l["user_id"] for l in response.json()] == [admin["id"]]


def test_clan_icon(client: TestClient, user: dict, clan_icon: str):
    clan_name, clan_tag = "Zaitev's Snore Club", "^123(Zzz"

    # Try bad image
    response = client.post(
        "/v1/clan/register",
        json=dict(tag=clan_tag, name=clan_name, icon=clan_icon + "hi"),
        auth=user["auth"],
    )
    assert response.status_code == 422

    # Properly register clan
    response = client.post(
        "/v1/clan/register",
        json=dict(tag=clan_tag, name=clan_name, icon=clan_icon),
        auth=user["auth"],
    )
    assert response.status_code == 200
    clan = response.json()

    # Change icon to one that is too big
    response = client.post(
        "/v1/clan/update-icon",
        json=dict(clan_id=clan["id"], icon=get_random_icon(64, 128)),
        auth=user["auth"],
    )
    assert response.status_code == 422

    # Properly change it
    new_icon = get_random_icon(64, 64)
    response = client.post(
        "/v1/clan/update-icon",
        json=dict(clan_id=clan["id"], icon=new_icon),
        auth=user["auth"],
    )
    assert response.status_code == 200
    assert response.json()["icon"] != clan["icon"]
