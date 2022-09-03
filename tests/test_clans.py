from fastapi.testclient import TestClient

from tests.utils import dict_without_key


def test_clan_registration(client: TestClient, user: dict, clan_icon: str):
    # Register a new clan.
    clan_name, clan_tag = "Zaitev's Snore Club", "Zzz"
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
        json=dict(clan_id=clan["id"]),
        auth=user["auth"],
    )
    assert clan == response.json()

    # Get clan members
    response = client.get(
        "/v1/clan/members",
        json=dict(clan_id=clan["id"]),
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

    response = client.get(
        "/v1/clan/by-id/batch",
        json=dict(clan_ids=[1, 2]),
        auth=user["auth"],
    ).json()
    assert type(response) is list
    assert len(response) == 1


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
        "/v1/clan/accept-invite",
        json=dict(clan_id=clan["id"]),
        auth=nonadmin["auth"],
    )
    assert response.status_code == 401

    # There are (still) no invites.
    response = client.get(
        "/v1/clan/invites",
        json=dict(clan_id=clan["id"]),
        auth=admin["auth"],
    )
    assert response.json() == []

    # Admin is the only member.
    response = client.get(
        "/v1/clan/members",
        json=dict(clan_id=clan["id"]),
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
        json=dict(user_id=admin["id"]),
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
        json=dict(clan_id=clan["id"]),
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
        "/v1/clan/accept-invite",
        json=dict(clan_id=clan["id"]),
        auth=nonadmin["auth"],
    )
    assert response.status_code == 200

    # Both admin and non-admin are now members.
    response = client.get(
        "/v1/clan/members",
        json=dict(clan_id=clan["id"]),
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
