from fastapi.testclient import TestClient

from metaserver import email


def dict_without_key(d, k):
    d2 = d.copy()
    del d2[k]
    return d2


def register_user(client: TestClient, username: str, password: str):
    user = client.post(
        "/v1/user/register",
        json=dict(username=username, display_name="foo", password=password),
    ).json()

    mail_token = email.TOKEN_CACHE_REVERSE[user["id"]]

    user = client.post(
        "/v1/user/email/verify",
        json=dict(mail_token=mail_token),
        auth=(username, password),
    ).json()

    # Add credentials for testing purposes.
    user["auth"] = (username, password)
    return user
