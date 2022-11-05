import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from metaserver import email
import metaserver.database.api as db
from metaserver.api import app
from metaserver.database.models import *

from tests import utils


@pytest.fixture(scope="function")
def client():
    db.engine = create_engine(
        "sqlite://",
        connect_args=dict(check_same_thread=False),
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(db.engine)

    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def no_email_sending(monkeypatch):
    """Don't send email during tests."""

    def do_nothing(recipient, token):
        pass

    monkeypatch.setattr(email, "send_verification_email", do_nothing)


@pytest.fixture
def user(client: TestClient):
    return utils.register_user(
        client,
        display_name="foo",
        username="foo@example.com",
        password="12345678",
    )


@pytest.fixture
def user2(client: TestClient):
    return utils.register_user(
        client,
        display_name="foo2",
        username="foo2@example.com",
        password="12345678",
    )


@pytest.fixture
def server(client: TestClient, user: dict):
    server_create = dict(
        host_name="https://example.com",
        port=11235,
        display_name="Zaitev's Snooze Server",
        description="Welcome, grab a pillow.",
        game_type="Snoozing",
        max_player_count=42,
    )
    server_login = client.post(
        "/v1/server/register",
        json=server_create,
        auth=user["auth"],
    ).json()

    user_servers = client.get("/v1/server/list/my", auth=user["auth"]).json()

    return {
        "auth": (server_login["username"], server_login["password"]),
        "id": user_servers[0]["id"],
    }


@pytest.fixture
def clan_icon():
    return "iVBORw0KGgoAAAANSUhEUgAAAEAAAABAAQMAAACQp+OdAAAAA1BMVEX///+nxBvIAAAAD0lEQVR4nGNgGAWjgHwAAAJAAAFZNqEDAAAAAElFTkSuQmCC"
