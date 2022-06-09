from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

import metaserver.database.api as db
from metaserver import auth
from metaserver.database import models

app = FastAPI()


@app.on_event("startup")
def on_startup():
    db.init()


@app.get("/")
def index():
    """Check if server is alive."""
    return "OK"


@app.post("/v1/user/login")
def user_login(
    user: models.UserLogin = Depends(auth.auth_user),
    *,
    session: Session = Depends(db.get_session),
):
    """Verify user credentials."""
    return


@app.post("/v1/user/register")
def user_register(
    new_user: models.UserCreate,
    *,
    session: Session = Depends(db.get_session),
):
    """Register a new user."""
    key, salt = auth.new_password(new_user.password)
    user = models.User(
        username=new_user.username,
        display_name=new_user.display_name,
        key=key,
        salt=salt,
    )
    try:
        db.create_user(session, user)
    except IntegrityError:
        # The username is taken.
        raise HTTPException(status.HTTP_409_CONFLICT)


@app.get("/v1/clan/members", response_model=list[models.ReadUser])
def clan_members(
    clan_tag: Optional[str] = None,
    clan_id: Optional[int] = None,
    *,
    session: Session = Depends(db.get_session),
    user: models.UserLogin = Depends(auth.auth_user),
):
    if clan_tag:
        return db.get_clan_members_by_tag(session, clan_tag)
    elif clan_id:
        return db.get_clan_members_by_id(session, clan_id)
    raise HTTPException(status.HTTP_400_BAD_REQUEST)


@app.post("/v1/clan/register", response_model=models.Clan)
def clan_register(
    new_clan: models.ClanCreate,
    *,
    session: Session = Depends(db.get_session),
    user: models.UserLogin = Depends(auth.auth_user),
):
    try:
        return db.create_clan(session, user, new_clan)
    except ValidationError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY)
