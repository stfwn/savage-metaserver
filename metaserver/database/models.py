from datetime import datetime
from typing import Optional

from sqlmodel import VARCHAR, Column, Field, Relationship, SQLModel, create_engine


class UserClanLink(SQLModel, table=True):
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


class ClanSkinLink(SQLModel, table=True):
    skin_id: Optional[int] = Field(
        default=None, foreign_key="skin.id", primary_key=True
    )
    clan_id: Optional[int] = Field(
        default=None, foreign_key="clan.id", primary_key=True
    )

    skin: "Skin" = Relationship(back_populates="clan_links")
    clan: "Clan" = Relationship(back_populates="skin_links")


class UserSkinLink(SQLModel, table=True):
    skin_id: Optional[int] = Field(
        default=None, foreign_key="skin.id", primary_key=True
    )
    user_id: Optional[int] = Field(
        default=None, foreign_key="user.id", primary_key=True
    )

    skin: "Skin" = Relationship(back_populates="user_links")
    user: "User" = Relationship(back_populates="skin_links")


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(
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
    skin_links: list[UserSkinLink] = Relationship(back_populates="user")


class Clan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tag: str = Field(sa_column=Column("tag", VARCHAR, unique=True, nullable=False))
    name: str = Field(sa_column=Column("name", VARCHAR, unique=True, nullable=False))
    created: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    deleted: Optional[datetime]

    user_links: list[UserClanLink] = Relationship(back_populates="clan")
    skin_links: list[ClanSkinLink] = Relationship(back_populates="clan")


class Skin(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: Optional[str]
    kind: str
    unit: str
    model_path: str

    user_links: list[UserSkinLink] = Relationship(back_populates="skin")
    clan_links: list[ClanSkinLink] = Relationship(back_populates="skin")
