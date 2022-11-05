import os
from datetime import datetime

from sqlalchemy.exc import NoResultFound
from sqlmodel import Session, SQLModel, col, create_engine, select
from sqlmodel.pool import StaticPool

import metaserver.database.patch  # Bugfix in SQLModel
from metaserver.database.models import Clan, Skin, User, UserClanLink, Server, UserStats
from metaserver.database.utils import UserClanLinkRank
from metaserver.schemas import ClanCreate, ServerUpdate
from metaserver import config

if config.database_url == "sqlite://":
    engine = create_engine(
        config.database_url,
        connect_args={"check_same_thread": False},
        echo=config.dev_mode,
        poolclass=StaticPool,
    )
else:
    engine = create_engine(
        config.database_url,
        echo=config.dev_mode,
        connect_args={"check_same_thread": False},
    )


def dev_mode_startup():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


###########
# General #
###########


def commit_and_refresh(
    session: Session, model: Clan | Skin | User | UserClanLink | Server
):
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def commit_and_refresh_batch(
    session: Session,
    models: list[Clan | Skin | User | UserClanLink | Server | UserStats],
):
    for model in models:
        session.add(model)
    session.commit()
    for model in models:
        session.refresh(model)
    return models


########
# User #
########


def get_user_by_id(session: Session, user_id: int) -> User | None:
    try:
        return session.exec(select(User).where(User.id == user_id)).one()
    except NoResultFound:
        return None


def get_users_by_id(session: Session, user_ids: list[int]) -> list[User]:
    return session.exec(select(User).where(col(User.id).in_(user_ids))).all()


def get_user_by_username(session: Session, username: str) -> User | None:
    try:
        return session.exec(select(User).where(User.username == username)).one()
    except NoResultFound:
        return None


def set_user_last_online_now(session: Session, user: User):
    user.last_online = datetime.utcnow()
    return commit_and_refresh(session, user)


def set_user_last_online_now_by_id(session: Session, user_id: int):
    user = get_user_by_id(session, user_id)
    set_user_last_online_now(session, user)


################
# UserClanLink #
################


def get_user_clan_link(
    session: Session,
    user_id: int,
    clan_id: int,
) -> UserClanLink | None:
    try:
        return session.exec(
            select(UserClanLink).where(
                UserClanLink.user_id == user_id,
                UserClanLink.clan_id == clan_id,
            )
        ).one()
    except NoResultFound:
        return None


#########
# Stats #
#########


def get_user_stats(
    session: Session,
    user_id: int,
    server_id: int,
) -> UserStats | None:
    """Fetches UserStats for the requested user-server pairs in batch form.
    Users that have never played on the server will be excluded from the
    result."""
    try:
        return session.exec(
            select(UserStats).where(
                UserStats.user_id == user_id,
                UserStats.server_id == server_id,
            )
        ).one()
    except NoResultFound:
        return None


def get_user_stats_batch(
    session: Session,
    user_ids: list[int],
    server_id: int,
) -> list[UserStats]:
    """Fetches UserStats for the requested user-server pairs in batch form.
    Users that have never played on the server will be excluded from the
    result."""
    return session.exec(
        select(UserStats).where(
            col(UserStats.user_id).in_(user_ids),
            UserStats.server_id == server_id,
        )
    ).all()


########
# Clan #
########


def create_clan(session: Session, user: User, new_clan: ClanCreate) -> Clan:
    clan = Clan(**new_clan.dict())
    link = UserClanLink(
        user=user,
        clan=clan,
        rank=UserClanLinkRank.OWNER,
        joined=datetime.utcnow(),
    )
    session.add(link)
    session.commit()
    session.refresh(clan)
    return clan


def get_all_clans(session: Session):
    return session.exec(select(Clan)).all()


def get_clan_by_id(session: Session, clan_id: int) -> Clan | None:
    try:
        return session.exec(select(Clan).where(Clan.id == clan_id)).one()
    except NoResultFound:
        return None


def get_clans_by_id(session: Session, clan_ids: list[int]) -> list[Clan]:
    return session.exec(select(Clan).where(col(Clan.id).in_(clan_ids))).all()


def get_clan_user_invites(session: Session, clan_id: int) -> list[UserClanLink]:
    clan = get_clan_by_id(session, clan_id)
    return [link for link in clan.user_links if link.is_open_invitation]


def invite_user_to_clan(session: Session, user_id: int, clan_id: int):
    """Creates a clan invitation to clan for user. Responsibility of checking
    for legality is on the caller."""
    link = UserClanLink(user_id=user_id, clan_id=clan_id)
    session.add(link)
    session.commit()


##########
# Server #
##########


def create_server(session: Session, user: User, server: Server):
    session.add(server)
    session.commit()
    session.refresh(server)
    return server


def get_server_by_id(session: Session, server_id: int) -> Server:
    return session.exec(select(Server).where(Server.id == server_id)).one()


def get_online_servers(session: Session, cutoff: datetime):
    return session.exec(select(Server).where(Server.updated > cutoff)).all()


def update_server(session: Session, server: Server, server_update: ServerUpdate):
    for k, v in server_update:
        if k == "host_name":
            v = str(v)
        setattr(server, k, v)
    session.add(server)
    session.commit()
    session.refresh(server)
    return server


########
# Skin #
########


def get_skins_for_user_by_id(session: Session, user_id: int) -> list[Skin]:
    user = get_user_by_id(session, user_id)
    return [link.skin for link in user.skin_links]


def get_skins_for_clan_by_id(session: Session, clan_id: int) -> list[Skin]:
    clan = get_clan_by_id(session, clan_id)
    return [link.skin for link in clan.skin_links]
