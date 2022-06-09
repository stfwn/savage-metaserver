from fastapi.testclient import TestClient
import pytest

import metaserver


def test_user_auth(client: TestClient):
    correct_pw = "12345678"
    wrong_pw = correct_pw + "bad"
    too_short_pw = correct_pw[:3]
    too_long_pw = wrong_pw * 1000

    # Log in with non-existent user.
    response = client.post(
        "/v1/user/login",
        headers={
            "username": "foo",
            "password": "bar",
        },
    )
    assert response.status_code == 401

    # Register a new user.
    response = client.post(
        "/v1/user/register",
        json={"username": "foo@example.com", "password": correct_pw},
    )
    assert response.status_code == 200

    # Register a new user with taken username.
    response = client.post(
        "/v1/user/register",
        json={"username": "foo@example.com", "password": correct_pw},
    )
    assert response.status_code == 409

    # Register a new user with email that is not an email.
    response = client.post(
        "/v1/user/register",
        json={"username": "foo", "password": correct_pw},
    )
    assert response.status_code == 422

    # Register a new user with password that is too short.
    response = client.post(
        "/v1/user/register",
        json={"username": "foo2@example.com", "password": too_short_pw},
    )

    assert response.status_code == 422
    # Register a new user with password that is too long.
    response = client.post(
        "/v1/user/register",
        json={"username": "foo2@example.com", "password": too_long_pw},
    )
    assert response.status_code == 422

    # Login with correct password.
    response = client.post("/v1/user/login", auth=("foo@example.com", correct_pw))
    assert response.status_code == 200

    # Login with wrong password.
    response = client.post("/v1/user/login", auth=("foo@example.com", wrong_pw))
    assert response.status_code == 401
