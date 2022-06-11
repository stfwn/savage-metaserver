import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import EmailStr, SecretStr, ValidationError
from sqlmodel import (
    VARCHAR,
    Column,
    Field,
    Relationship,
    SQLModel,
    String,
    create_engine,
)


class UserClanLink(SQLModel, table=True):
    """Many-to-many link between User and Clan."""

    clan_id: Optional[int] = Field(
        default=None, foreign_key="clan.id", primary_key=True
    )
    user_id: Optional[int] = Field(
        default=None, foreign_key="user.id", primary_key=True
    )

    clan: "Clan" = Relationship(back_populates="user_links")
    user: "User" = Relationship(back_populates="clan_links")

    is_admin: bool = False
    invited: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    joined: Optional[datetime]
    deleted: Optional[datetime]


class User(SQLModel, table=True):
    """User object in the database."""

    id: Optional[int] = Field(default=None, primary_key=True)
    username: EmailStr = Field(
        sa_column=Column("username", VARCHAR, unique=True, nullable=False)
    )
    display_name: str
    key: str
    salt: str
    created: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    verified: Optional[datetime]
    deleted: Optional[datetime]
    deleted_reason: Optional[str]

    clan_links: list[UserClanLink] = Relationship(back_populates="user")


class Clan(SQLModel, table=True):
    """Clan object in the database."""

    id: Optional[int] = Field(default=None, primary_key=True)
    tag: str = Field(sa_column=Column("tag", VARCHAR, unique=True, nullable=False))
    name: str = Field(sa_column=Column("name", VARCHAR, unique=True, nullable=False))
    created: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    deleted: Optional[datetime]

    user_links: list[UserClanLink] = Relationship(back_populates="clan")
