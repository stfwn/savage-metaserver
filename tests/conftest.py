import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import metaserver.database.api as db
from metaserver.api import app
from metaserver.database.models import *


@pytest.fixture
def client():
    db.engine = create_engine(
        "sqlite://",
        connect_args=dict(check_same_thread=False),
        poolclass=StaticPool,
    )

    with TestClient(app) as client:
        yield client
