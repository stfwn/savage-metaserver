import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import EmailStr, SecretStr, ValidationError, constr, validator
from sqlmodel import (
    VARCHAR,
    Column,
    Field,
    Relationship,
    SQLModel,
    String,
    create_engine,
)

from metaserver.database import utils


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


########
# User #
########


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


class UserRead(SQLModel):
    """User object that is returned when the outside world asks for a user."""

    id: int
    display_name: str
    created: datetime


class UserCreate(SQLModel):
    """User object that is posted to register a new user."""

    username: EmailStr
    display_name: str = Field(min_length=1, max_length=32)
    password: SecretStr = Field(min_length=8, max_length=32)


class UserLogin(SQLModel):
    """User object that is posted to login."""

    username: EmailStr
    password: SecretStr = Field(min_length=8, max_length=32)


########
# Clan #
########


class Clan(SQLModel, table=True):
    """Clan object in the database."""

    id: Optional[int] = Field(default=None, primary_key=True)
    tag: str = Field(sa_column=Column("tag", VARCHAR, unique=True, nullable=False))
    name: str = Field(sa_column=Column("name", VARCHAR, unique=True, nullable=False))
    created: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    deleted: Optional[datetime]

    user_links: list[UserClanLink] = Relationship(back_populates="clan")

    _validate_tag = validator("tag", allow_reuse=True)(utils.validate_tag)


class ClanCreate(SQLModel):
    """Clan object when the outside world wants to create a new clan."""

    tag: str
    name: str

    _validate_tag = validator("tag", allow_reuse=True)(utils.validate_tag)
