from fastapi.testclient import TestClient

from metaserver import email
from tests.utils import dict_without_key


def test_user_registration(client: TestClient):
    username = "foo@example.com"
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
        json=dict(username=username, display_name="foo", password=correct_pw),
    )
    assert response.status_code == 200

    # Check that they can't log in yet.
    user = response.json()
    response = client.get(
        "/v1/user/by-id",
        json=dict(user_id=user["id"]),
        auth=(username, correct_pw),
    )
    assert response.status_code == 401

    # Verify the user's email
    mail_token = email.TOKEN_CACHE_REVERSE[user["id"]]
    response = client.post(
        "/v1/user/email/verify",
        json=dict(mail_token=mail_token),
        auth=(username, correct_pw),
    )
    assert response.status_code == 200

    # Check that the user can log in now by getting the user itself.
    response = client.get(
        "/v1/user/by-id",
        json=dict(user_id=user["id"]),
        auth=(username, correct_pw),
    )
    assert response.json() == dict_without_key(user, "proof")

    # Register a new user with taken username.
    response = client.post(
        "/v1/user/register",
        json=dict(username=username, display_name="foo", password=correct_pw),
    )
    assert response.status_code == 409

    # Register a new user with display name that is too long.
    response = client.post(
        "/v1/user/register",
        json=dict(username=username, display_name="foo" * 100, password=correct_pw),
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
    response = client.post("/v1/user/login", auth=(username, correct_pw))
    assert response.status_code == 200

    # Login with wrong password.
    response = client.post("/v1/user/login", auth=(username, wrong_pw))
    assert response.status_code == 401


def test_user_mail_tokens(client: TestClient):
    auth = ("foo@example.com", "12345678")
    # Register a new user to test mail tokens more
    user = client.post(
        "/v1/user/register",
        json=dict(username=auth[0], display_name="foo", password=auth[1]),
    ).json()

    response = client.post(
        "/v1/user/email/verify", json=dict(mail_token="short"), auth=auth
    )
    assert response.status_code == 422
    response = client.post(
        "/v1/user/email/verify", json=dict(mail_token="looooong"), auth=auth
    )
    assert response.status_code == 422
    response = client.post(
        "/v1/user/email/verify", json=dict(mail_token="wrongg"), auth=auth
    )
    assert response.status_code == 403

    # Request new token too soon
    response = client.post("/v1/user/email/renew-token", auth=auth)
    assert response.status_code == 403
    assert "wait" in response.json()["detail"].lower()

    # Request new token
    def get_big_number(user_id):
        return 1_000_000

    old_mail_token = email.TOKEN_CACHE_REVERSE[user["id"]]
    email.get_token_age_for_user = get_big_number
    response = client.post("/v1/user/email/renew-token", auth=auth)
    assert response.status_code == 200
    new_mail_token = email.TOKEN_CACHE_REVERSE[user["id"]]

    # Try to verify with old token
    response = client.post(
        "/v1/user/email/verify", json=dict(mail_token=old_mail_token), auth=auth
    )
    assert response.status_code == 403

    # Verify with new token
    response = client.post(
        "/v1/user/email/verify", json=dict(mail_token=new_mail_token), auth=auth
    )
    assert response.status_code == 200

    # Check that their auth is functioning now
    response = client.get(
        "/v1/user/by-id",
        json=dict(user_id=user["id"]),
        auth=auth,
    )
    assert response.status_code == 200

    # Try to claim another new email token
    response = client.post("/v1/user/email/renew-token", auth=auth)
    assert response.status_code == 403


def test_user_display_name(client: TestClient, user: dict):
    # Change display name.
    new_display_name = "bar"
    response = client.post(
        "/v1/user/change-display-name",
        json=dict(display_name=new_display_name),
        auth=user["auth"],
    )
    assert response.json()["display_name"] == new_display_name

    # Verify that the change persisted.
    user["display_name"] = new_display_name
    response = client.get(
        "/v1/user/by-id", json=dict(user_id=user["id"]), auth=user["auth"]
    )
    assert response.json() == dict_without_key(dict_without_key(user, "proof"), "auth")

    # Attempt to change to a display name that is too long
    new_display_name *= 80
    response = client.post(
        "/v1/user/change-display-name",
        json=dict(display_name=new_display_name),
        auth=user["auth"],
    )
    assert response.status_code == 422


def test_user_proof(client: TestClient, user: dict, user2: dict):
    # Verify user's proof using user's login.
    response = client.post(
        "/v1/user/verify-user-proof",
        json=dict(
            user_id=user["id"],
            user_proof=user["proof"],
        ),
        auth=user["auth"],
    )
    assert response.json() == True

    # Verify user's proof using user2's login.
    response = client.post(
        "/v1/user/verify-user-proof",
        json=dict(
            user_id=user["id"],
            user_proof=user["proof"],
        ),
        auth=user2["auth"],
    )
    assert response.json() == True
