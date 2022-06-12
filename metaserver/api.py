from typing import Optional

from fastapi import Body, Depends, FastAPI, HTTPException, status
from pydantic import Field, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

import metaserver.database.api as db
from metaserver import auth
from metaserver.database.models import Clan, User, UserClanLink
from metaserver.schemas import ClanCreate, UserCreate, UserLogin, UserRead

app = FastAPI()


@app.on_event("startup")
def on_startup():
    db.init()


@app.get("/")
def index():
    """Check if server is alive."""
    return "OK"


############
# /v1/user #
############


@app.get("/v1/user/by-id", response_model=UserRead)
def user(
    user_id: int = Body(embed=True),
    *,
    user: UserLogin = Depends(auth.auth_user),
    session: Session = Depends(db.get_session),
):
    return db.get_user_by_id(session, user_id)


@app.get("/v1/user/clan-invites", response_model=list[UserClanLink])
def user_clan_invites(
    *,
    user: UserLogin = Depends(auth.auth_user),
    session: Session = Depends(db.get_session),
):
    return db.get_user_clan_invites(session, user)


@app.post("/v1/user/login", response_model=UserRead)
def user_login(
    *,
    user: UserLogin = Depends(auth.auth_user),
    session: Session = Depends(db.get_session),
):
    """Verify user credentials."""
    return user


@app.post("/v1/user/register", response_model=UserRead)
def user_register(
    new_user: UserCreate,
    *,
    session: Session = Depends(db.get_session),
):
    """Register a new user."""
    key, salt = auth.new_password(new_user.password)
    user = User(
        username=new_user.username,
        display_name=new_user.display_name,
        key=key,
        salt=salt,
    )
    try:
        return db.create_user(session, user)
    except IntegrityError:
        # The username is taken.
        raise HTTPException(status.HTTP_409_CONFLICT)


@app.post("/v1/user/verify-clan-membership")
def user_verify_clan_membership(
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    return db.user_is_clan_member(session, user, clan_id)


@app.post("/v1/user/change-display-name", response_model=UserRead)
def user_change_display_name(
    display_name: str = Body(embed=True, min_length=1, max_length=64),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    return db.change_display_name(session, user, display_name)


############
# /v1/clan #
############


@app.get("v1/clan/all", response_model=list[Clan])
def clan(
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    return db.get_all_clans(session)


@app.get("/v1/clan/by-id", response_model=Clan)
def clan_by_id(
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    return db.get_clan_by_id(session, clan_id)


@app.post("/v1/clan/accept-invite")
def clan_accept_invite(
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if db.user_is_invited_to_clan(session, user, clan_id):
        db.accept_clan_invite(session, user, clan_id)
    else:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)


@app.post("/v1/clan/invite")
def clan_invite(
    user_id: int = Body(embed=True),
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if db.user_is_clan_admin(session, user, clan_id):
        db.invite_user_to_clan(session, user_id, clan_id)
    else:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)


@app.get("/v1/clan/invites")
def clan_invites(
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if db.user_is_clan_admin(session, user, clan_id):
        return db.get_clan_user_invites(session, clan_id)


@app.get("/v1/clan/members", response_model=list[UserRead])
def clan_members(
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    return db.get_clan_members(session, clan_id)


@app.post("/v1/clan/register", response_model=Clan)
def clan_register(
    new_clan: ClanCreate,
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    try:
        return db.create_clan(session, user, new_clan)
    except ValidationError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY)
