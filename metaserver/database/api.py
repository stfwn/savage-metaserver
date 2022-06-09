import os

from sqlmodel import Session, SQLModel, create_engine, select

from metaserver.database.models import User
from metaserver.database import constants


engine = create_engine(
    constants.database_url,
    echo=bool(os.environ.get("DEV", False)),
)


def init():
    SQLModel.metadata.create_all(engine)


def create_user(user: User):
    with Session(engine) as session:
        session.add(user)
        session.commit()


def get_user_by_username(username: str):
    with Session(engine) as session:
        return session.exec(select(User).where(User.username == username)).first()
