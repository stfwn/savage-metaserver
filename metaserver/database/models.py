from datetime import datetime
import random
import string
from typing import Literal, Optional

from sqlmodel import VARCHAR, Column, Field, JSON, Relationship, SQLModel, create_engine

from metaserver import config
from metaserver.database.utils import UserClanLinkDeletedReason, UserClanLinkRank


class UserClanLink(SQLModel, table=True):
    clan_id: int | None = Field(default=None, foreign_key="clan.id", primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)

    clan: "Clan" = Relationship(back_populates="user_links")
    user: "User" = Relationship(back_populates="clan_links")

    rank: UserClanLinkRank = UserClanLinkRank.MEMBER
    invited: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    joined: datetime | None
    deleted: datetime | None
    deleted_reason: UserClanLinkDeletedReason | None

    @property
    def is_membership(self):
        return bool(self.joined and not self.deleted)

    @property
    def is_declined_invitation(self):
        return bool(
            not self.joined
            and self.deleted
            and self.deleted_reason is UserClanLinkDeletedReason.DECLINED
        )

    @property
    def is_open_invitation(self):
        return not (self.joined or self.deleted)

    @property
    def is_retracted_invitation(self):
        return bool(
            not self.joined
            and self.deleted
            and self.deleted_reason is UserClanLinkDeletedReason.RETRACTED
        )

    @property
    def user_left_clan(self):
        return bool(
            self.joined
            and self.deleted
            and self.deleted_reason is UserClanLinkDeletedReason.LEFT
        )

    @property
    def user_was_kicked(self):
        return bool(
            self.joined
            and self.deleted
            and self.deleted_reason == UserClanLinkDeletedReason.KICKED
        )


class ClanSkinLink(SQLModel, table=True):
    skin_id: int | None = Field(default=None, foreign_key="skin.id", primary_key=True)
    clan_id: int | None = Field(default=None, foreign_key="clan.id", primary_key=True)

    skin: "Skin" = Relationship(back_populates="clan_links")
    clan: "Clan" = Relationship(back_populates="skin_links")


class UserSkinLink(SQLModel, table=True):
    skin_id: int | None = Field(default=None, foreign_key="skin.id", primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)

    skin: "Skin" = Relationship(back_populates="user_links")
    user: "User" = Relationship(back_populates="skin_links")


class UserStats(SQLModel, table=True):
    """Maintains running stats per user per server."""

    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)
    server_id: int | None = Field(
        default=None, foreign_key="server.id", primary_key=True
    )

    user: "User" = Relationship(back_populates="stats")
    server: "Server" = Relationship(back_populates="user_stats")

    first_seen: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_seen: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    matches_played_field: int = 0
    matches_played_command: int = 0
    matches_won_field: int = 0
    matches_won_command: int = 0
    skill_rating: int = config.initial_user_skill_rating


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(
        sa_column=Column("username", VARCHAR, unique=True, nullable=False)
    )
    display_name: str = Field(
        sa_column=Column("display_name", VARCHAR, unique=True, nullable=False)
    )
    key: str
    salt: str
    created: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    verified_email: datetime | None
    deleted: datetime | None
    deleted_reason: str | None
    last_online: datetime | None

    stats: list[UserStats] = Relationship(back_populates="user")
    clan_links: list[UserClanLink] = Relationship(back_populates="user")
    email_token: Optional["EmailToken"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    skin_links: list[UserSkinLink] = Relationship(back_populates="user")
    servers: list["Server"] = Relationship(back_populates="user")


class Clan(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    tag: str = Field(sa_column=Column("tag", VARCHAR, unique=True, nullable=False))
    name: str = Field(sa_column=Column("name", VARCHAR, unique=True, nullable=False))
    created: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    deleted: datetime | None
    icon: str

    user_links: list[UserClanLink] = Relationship(back_populates="clan")
    skin_links: list[ClanSkinLink] = Relationship(back_populates="clan")


class Skin(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    description: str | None
    kind: str
    unit: str
    model_path: str

    user_links: list[UserSkinLink] = Relationship(back_populates="skin")
    clan_links: list[ClanSkinLink] = Relationship(back_populates="skin")


class Server(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    key: str
    salt: str
    host_name: str
    port: int
    display_name: str
    description: str
    game_type: str
    current_player_count: int = 0
    current_map: str = ""
    max_player_count: int
    created: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated: datetime | None
    deleted: datetime | None
    deleted_reason: str | None

    # matches: list["Match"] = Relationship(back_populates="server")
    user_id: int = Field(default=None, foreign_key="user.id")
    user: User = Relationship(back_populates="servers")
    user_stats: list[UserStats] = Relationship(back_populates="server")


class EmailToken(SQLModel, table=True):
    created: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    user_id: int = Field(default=None, primary_key=True, foreign_key="user.id")
    key: str = Field(default_factory=lambda: EmailToken.new_key())

    user: User = Relationship(
        back_populates="email_token", sa_relationship_kwargs={"uselist": False}
    )

    @staticmethod
    def new_key():
        key_length = 6
        chars = string.ascii_uppercase.replace("I", "").replace("L", "")
        return "".join(random.choice(chars) for i in range(key_length))


#########
# Match #
#########


# class Match(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     server_id: int = Field(default=None, foreign_key="server.id")
#     server: "Server" = Relationship(back_populates="matches")
#     updates: list[MatchUpdate]
#     started: datetime
#     ended: Optional[datetime]


# class MatchUpdate(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     data: dict = Field(sa_column=Column(JSON))

#     class Config:
#         arbitrary_types_allowed = True
