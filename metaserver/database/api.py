import os

from sqlmodel import Session, SQLModel, create_engine, select

from metaserver.database import constants
from metaserver.database.models import Clan, ClanCreate, UserClanLink, User
import metaserver.database.patch


engine = create_engine(
    constants.database_url,
    echo=bool(os.environ.get("DEV", False)),
)


def init():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def create_user(session: Session, user: User):
    session.add(user)
    session.commit()


def get_user_by_username(session: Session, username: str) -> User:
    return session.exec(select(User).where(User.username == username)).first()


def create_clan(session: Session, user: User, new_clan: ClanCreate) -> Clan:
    clan = Clan(tag=new_clan.tag, name=new_clan.name)
    user_clan_link = UserClanLink(user=user, clan=clan, is_admin=True)
    session.add(user_clan_link)
    session.commit()
    session.refresh(clan)
    return clan


def get_clan_members_by_id(session: Session, clan_id: int) -> list[User]:
    clan = session.exec(select(Clan).where(Clan.id == clan_id)).one()
    return [link.user for link in clan.user_links]


def get_clan_members_by_tag(session: Session, clan_tag: str) -> list[User]:
    clan = session.exec(select(Clan).where(Clan.tag == clan_tag)).one()
    return [link.user for link in clan.user_links]
