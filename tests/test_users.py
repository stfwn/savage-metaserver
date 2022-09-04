from fastapi.testclient import TestClient

from metaserver import email


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
        params=dict(user_id=user["id"]),
        auth=(username, correct_pw),
    )
    assert response.status_code == 401

    # Registering with a taken display name should fail
    response = client.post(
        "/v1/user/register",
        json=dict(username="2" + username, display_name="foo", password=correct_pw),
    )
    assert response.status_code == 409

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
        params=dict(user_id=user["id"]),
        auth=(username, correct_pw),
    )
    assert response.json()["id"] == user["id"]

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
    old_mail_token = email.TOKEN_CACHE_REVERSE[user["id"]]
    get_big_number = lambda user_id: 1_000_000
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
        params=dict(user_id=user["id"]),
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
        "/v1/user/by-id", params=dict(user_id=user["id"]), auth=user["auth"]
    )
    assert response.json()["display_name"] == user["display_name"]

    # Attempt to change to a display name that is too long
    new_display_name *= 80
    response = client.post(
        "/v1/user/change-display-name",
        json=dict(display_name=new_display_name),
        auth=user["auth"],
    )
    assert response.status_code == 422


def test_user_proof(client: TestClient, user: dict):
    # Get user's last online datetime
    last_online_0 = client.get(
        "/v1/user/by-id",
        params=dict(user_id=user["id"]),
        auth=user["auth"],
    ).json()["last_online"]

    # Verify user's proof.
    response = client.post(
        "/v1/user/verify-user-proof",
        json=dict(
            user_id=user["id"],
            user_proof=user["proof"],
        ),
    )
    assert response.json() == True

    # Check that last online datetime was updated
    last_online_1 = client.get(
        "/v1/user/by-id",
        params=dict(user_id=user["id"]),
        auth=user["auth"],
    ).json()["last_online"]
    assert last_online_1 > last_online_0

    # Try to verify a wrong proof.
    response = client.post(
        "/v1/user/verify-user-proof",
        json=dict(
            user_id=user["id"],
            user_proof="blerb",
        ),
    )
    assert response.json() == False

    # Check that last online datetime was not updated
    last_online_2 = client.get(
        "/v1/user/by-id",
        params=dict(user_id=user["id"]),
        auth=user["auth"],
    ).json()["last_online"]
    assert last_online_2 == last_online_1


def test_get_user_batch(client: TestClient, user: dict, user2: dict):
    resp = client.get(
        "/v1/user/by-id/batch",
        params=dict(user_ids=[user["id"], user2["id"]]),
        auth=user["auth"],
    ).json()

    assert type(resp) == list
    assert len(resp) == 2
    assert [u["id"] for u in resp] == [user["id"], user2["id"]]
