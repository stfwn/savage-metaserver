from fastapi.testclient import TestClient
import pytest
from sqlmodel import create_engine
from sqlmodel.pool import StaticPool

from metaserver.api import app
import metaserver.database.api as db


@pytest.fixture
def client():
    db.engine = create_engine(
        "sqlite://",
        connect_args=dict(check_same_thread=False),
        poolclass=StaticPool,
    )
    with TestClient(app) as client:
        yield client
