from datetime import datetime
from typing import Optional

from pydantic import constr, EmailStr, SecretStr
from sqlmodel import Column, Field, SQLModel, String, VARCHAR, create_engine


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: EmailStr = Field(
        sa_column=Column("username", VARCHAR, unique=True, nullable=False)
    )
    key: str
    salt: str
    created: datetime = Field(default=datetime.utcnow, nullable=False)
    verified: Optional[datetime]
    deleted: Optional[datetime]
    deleted_reason: Optional[str]


class UserLogin(SQLModel):
    username: EmailStr
    password: SecretStr = Field(min_length=8, max_length=32)


class Clan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tag: str
    created: datetime = Field(default=datetime.utcnow, nullable=False)
    deleted: Optional[datetime]


class ClanMembership(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    clan_id: int
    user_id: int
    created: datetime = Field(default=datetime.utcnow, nullable=False)
    deleted: Optional[datetime]
