from fastapi.testclient import TestClient
import pytest
from sqlmodel import Session

from tests.utils import dict_without_key


def test_user_auth(client: TestClient):
    correct_pw = "12345678"
    wrong_pw = correct_pw + "bad"
    too_short_pw = correct_pw[:3]
    too_long_pw = wrong_pw * 1000

    # Log in with non-existent user.
    response = client.post(
        "/v1/user/login",
        headers=dict(username="foo", password="bar"),
    )
    assert response.status_code == 401

    # Register a new user.
    response = client.post(
        "/v1/user/register",
        json=dict(username="foo@example.com", display_name="foo", password=correct_pw),
    )
    assert response.status_code == 200

    # Get the user
    user = response.json()
    response = client.get(
        "/v1/user/by-id",
        json=dict(user_id=user["id"]),
        auth=("foo@example.com", correct_pw),
    )
    assert response.json() == dict_without_key(user, "proof")

    # Register a new user with taken username.
    response = client.post(
        "/v1/user/register",
        json=dict(username="foo@example.com", display_name="foo", password=correct_pw),
    )
    assert response.status_code == 409

    # Register a new user with display name that is too long.
    response = client.post(
        "/v1/user/register",
        json=dict(
            username="foo@example.com", display_name="foo" * 100, password=correct_pw
        ),
    )
    assert response.status_code == 422

    # Register a new user with email that is not an email.
    response = client.post(
        "/v1/user/register",
        json=dict(username="foo", password=correct_pw),
    )
    assert response.status_code == 422

    # Register a new user with password that is too short.
    response = client.post(
        "/v1/user/register",
        json=dict(username="foo2@example.com", password=too_short_pw),
    )

    assert response.status_code == 422
    # Register a new user with password that is too long.
    response = client.post(
        "/v1/user/register",
        json=dict(username="foo2@example.com", password=too_long_pw),
    )
    assert response.status_code == 422

    # Login with correct password.
    response = client.post("/v1/user/login", auth=("foo@example.com", correct_pw))
    assert response.status_code == 200

    # Login with wrong password.
    response = client.post("/v1/user/login", auth=("foo@example.com", wrong_pw))
    assert response.status_code == 401


def test_user_display_name(client: TestClient):
    auth = ("foo@example.com", "12345678")

    # Register a new user.
    user = client.post(
        "/v1/user/register",
        json=dict(username=auth[0], display_name="foo", password=auth[1]),
    ).json()

    # Change display name.
    new_display_name = "bar"
    response = client.post(
        "/v1/user/change-display-name",
        json=dict(display_name=new_display_name),
        auth=auth,
    )
    assert response.json()["display_name"] == new_display_name

    # Verify that the change persisted.
    user["display_name"] = new_display_name
    response = client.get("/v1/user/by-id", json=dict(user_id=user["id"]), auth=auth)
    assert response.json() == dict_without_key(user, "proof")

    # Attempt to change to a display name that is too long
    new_display_name *= 80
    response = client.post(
        "/v1/user/change-display-name",
        json=dict(display_name=new_display_name),
        auth=auth,
    )
    assert response.status_code == 422


def test_user_proof(client: TestClient):
    # Register two new users.
    user_0 = client.post(
        "/v1/user/register",
        json=dict(username="foo@example.com", display_name="foo", password="12345678"),
    ).json()

    # Register another user.
    user_1 = client.post(
        "/v1/user/register",
        json=dict(username="foo2@example.com", display_name="foo", password="12345678"),
    ).json()

    # Verify user 0's proof using user 0's login.
    response = client.post(
        "/v1/user/verify-user-proof",
        json=dict(
            user_id=user_0["id"],
            user_proof=user_0["proof"],
        ),
        auth=("foo@example.com", "12345678"),
    )
    assert response.json() == True

    # Verify user 0's proof using user 1's login.
    response = client.post(
        "/v1/user/verify-user-proof",
        json=dict(
            user_id=user_0["id"],
            user_proof=user_0["proof"],
        ),
        auth=("foo2@example.com", "12345678"),
    )
    assert response.json() == True
