import os
from datetime import datetime

from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

import metaserver.database.patch  # Bugfix in SQLModel
from metaserver.database.models import Clan, Skin, User, UserClanLink, Server
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
    engine = create_engine(config.database_url, echo=config.dev_mode)


def dev_mode_startup():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


########
# User #
########


def create_user(session: Session, user: User):
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_by_id(session: Session, user_id: int) -> User:
    return session.exec(select(User).where(User.id == user_id)).first()


def get_user_by_username(session: Session, username: str) -> User:
    return session.exec(select(User).where(User.username == username)).first()


def get_user_clan_invites(session: Session, user: User) -> list[UserClanLink]:
    return [link for link in user.clan_links if not (link.joined or link.deleted)]


def user_is_clan_admin(session: Session, user: User, clan_id: int) -> bool:
    for clan_link in user.clan_links:
        if clan_link.clan.id == clan_id:
            return clan_link.is_admin
    return False


def user_is_clan_member(session: Session, user: User, clan_id: int) -> bool:
    for clan_link in user.clan_links:
        if clan_link.clan.id == clan_id and clan_link.joined and not clan_link.deleted:
            return True
    return False


def user_is_invited_to_clan(session: Session, user: User, clan_id: int) -> bool:
    for clan_link in user.clan_links:
        if clan_link.clan.id == clan_id:
            return bool(clan_link.invited)
    return False


def accept_clan_invite(session: Session, user: User, clan_id: int):
    for clan_link in user.clan_links:
        if clan_link.clan.id == clan_id and not (clan_link.joined or clan_link.deleted):
            clan_link.joined = datetime.utcnow()
            session.add(clan_link)
    session.commit()


def change_display_name(session: Session, user: User, display_name: str) -> User:
    user.display_name = display_name
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def set_user_last_online_now(session: Session, user: User):
    user.last_online = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)


def set_user_last_online_now_by_id(session: Session, user_id: int):
    user = get_user_by_id(session, user_id)
    set_user_last_online_now(session, user)


def set_user_verified_email(session: Session, user: User):
    user.verified_email = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)


########
# Clan #
########


def create_clan(session: Session, user: User, new_clan: ClanCreate) -> Clan:
    clan = Clan(tag=new_clan.tag, name=new_clan.name)
    link = UserClanLink(user=user, clan=clan, is_admin=True, joined=datetime.utcnow())
    session.add(link)
    session.commit()
    session.refresh(clan)
    return clan


def get_all_clans(session: Session):
    return session.exec(select(Clan)).all()


def get_clan_by_id(session: Session, clan_id: int) -> Clan:
    return session.exec(select(Clan).where(Clan.id == clan_id)).one()


def get_clan_by_tag(session: Session, clan_tag: str) -> Clan:
    return session.exec(select(Clan).where(Clan.tag == clan_tag)).one()


def get_clan_user_invites(session: Session, clan_id: int) -> list[UserClanLink]:
    clan = get_clan_by_id(session, clan_id)
    return [link for link in clan.user_links if not (link.joined or link.deleted)]


def invite_user_to_clan(session: Session, user_id: int, clan_id: int):
    """Creates a clan invitation to clan for user. Responsibility of checking
    for legality is on the caller."""
    link = UserClanLink(user_id=user_id, clan_id=clan_id)
    session.add(link)
    session.commit()


def get_clan_members(session: Session, clan_id: int) -> list[User]:
    clan = get_clan_by_id(session, clan_id)
    return [link for link in clan.user_links if (link.joined and not link.deleted)]


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
