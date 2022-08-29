from datetime import datetime
import json

from fastapi import BackgroundTasks, Body, Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import Field, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

import metaserver.database.api as db
from metaserver import auth, config, email
from metaserver.database.models import Clan, Skin, User, UserClanLink, Server
from metaserver.schemas import (
    ClanCreate,
    ServerLogin,
    ServerCreate,
    ServerRead,
    ServerUpdate,
    UserCreate,
    UserLogin,
    UserRead,
    UserReadWithProof,
)

app = FastAPI()


@app.on_event("startup")
def on_startup():
    if config.dev_mode:
        db.dev_mode_startup()


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


@app.get("/v1/user/by-id/batch", response_model=list[UserRead])
def user(
    user_ids: list[int] = Body(embed=True),
    *,
    user: UserLogin = Depends(auth.auth_user),
    session: Session = Depends(db.get_session),
):
    return db.get_users_by_id(session, user_ids)


@app.get("/v1/user/clan-invites", response_model=list[UserClanLink])
def user_clan_invites(
    *,
    user: UserLogin = Depends(auth.auth_user),
    session: Session = Depends(db.get_session),
):
    return [link for link in user.clan_links if link.is_open_invitation]


@app.post("/v1/user/login", response_model=UserReadWithProof)
def user_login(
    *,
    user: UserLogin = Depends(auth.auth_user),
    session: Session = Depends(db.get_session),
):
    """Verify user credentials and obtain a user proof token. The user provides
    this token to a third party (like a game server) to prove that they are
    registered with this meta server. The third party then verifies this token
    using the `/v1/user/verify-user-proof` route.

    Because the implementation is cryptographic there's no need to store tokens
    in the database, but all user proof tokens are invalidated together
    periodically and whenever the server secret involved is refreshed. It is
    unlikely that user numbers are ever going to get so crazy that the wave of
    requests to this route after a token invalidation event overwhelms the
    server, but if this happens the system should be expanded so that each user
    should receive their own TTL token."""
    db.set_user_last_online_now(session, user)
    user_proof = auth.generate_user_proof(user.id)
    return UserReadWithProof(**user.dict(), proof=user_proof)


@app.post("/v1/user/verify-user-proof", response_model=bool)
def user_verify_user_proof(
    user_id: int = Body(embed=True),
    user_proof: str = Body(embed=True),
    *,
    background_tasks: BackgroundTasks,
    session: Session = Depends(db.get_session),
):
    """Verify user proof. See docstring for user login for more."""
    if auth.verify_user_proof(user_id, user_proof):
        background_tasks.add_task(db.set_user_last_online_now_by_id, session, user_id)
        return True
    return False


@app.post("/v1/user/register", response_model=UserReadWithProof)
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
        user = db.create_user(session, user)
        mail_token = email.generate_token(user.id)
        email.send_verification_email(recipient=user.username, token=mail_token)
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username taken")
    return UserReadWithProof(**user.dict(), proof=auth.generate_user_proof(user.id))


@app.post("/v1/user/verify-clan-membership")
def user_verify_clan_membership(
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    return db.user_is_clan_member(session, user, clan_id)


@app.post("/v1/user/email/verify", response_model=UserReadWithProof)
def user_email_verify(
    mail_token: str = Body(embed=True, min_length=6, max_length=6),
    *,
    background_tasks: BackgroundTasks,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_unverified_user),
):
    try:
        if email.verify_token(user.id, mail_token):
            db.set_user_verified_email(session, user)
            background_tasks.add_task(db.set_user_last_online_now, session, user)
            return UserReadWithProof(
                **user.dict(), proof=auth.generate_user_proof(user.id)
            )
        else:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Incorrect mail verification token"
            )
    except KeyError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No mail verification token found for user (request a new one)",
        )


@app.post("/v1/user/email/renew-token")
def user_email_new_token(
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_unverified_user),
):
    if user.verified_email:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User already verified mail")
    if email.get_token_age_for_user(user.id) <= 30:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Wait at least 30 seconds before requesting a new token",
        )
    mail_token = email.generate_token(user.id)
    email.send_verification_email(user.username, mail_token)
    return "Token sent"


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


@app.get("/v1/clan/all", response_model=list[Clan])
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


@app.get("/v1/clan/for-user/by-id", response_model=list[UserClanLink])
def clan_for_user_by_id(
    user_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if user_id != user.id:
        user = db.get_user_by_id(session, user_id)
    return [link for link in user.clan_links if link.is_membership]


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
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "User is not invited to join clan"
        )


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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is not clan admin")


@app.get("/v1/clan/invites", response_model=list[UserClanLink])
def clan_invites(
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if db.user_is_clan_admin(session, user, clan_id):
        return db.get_clan_user_invites(session, clan_id)


@app.get("/v1/clan/members", response_model=list[UserClanLink])
def clan_members(
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    clan = db.get_clan_by_id(session, clan_id)
    return [link for link in clan.user_links if link.is_membership]


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


############
# /v1/skin #
############


@app.get("/v1/skin/for-user/by-id", response_model=list[Skin])
def skin_for_user_by_id(
    user_id: int = Body(embed=True),
    clan_id: int | None = Body(default=None, embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    skins = db.get_skins_for_user_by_id(session, user_id)
    if clan_id:
        skins += db.get_skins_for_clan_by_id(session, clan_id)
    return skins


@app.get("/v1/skin/for-clan/by-id", response_model=list[Skin])
def skin_for_clan_by_id(
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    return db.get_skins_for_clan_by_id(session, clan_id)


##############
# /v1/server #
##############


@app.post("/v1/server/register", response_model=ServerLogin)
def server_register(
    new_server: ServerCreate,
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if len(user.servers) >= config.max_servers_per_user:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"User has reached the max number of servers of {config.max_servers_per_user}",
        )

    try:
        password = auth.generate_server_password()
        key, salt = auth.new_password(password)
        # Round trip to json is a workaround for pydantic not having a
        # hook to provide custom serializers for .dict()
        new_server = Server(
            **json.loads(new_server.json()), user=user, key=key, salt=salt
        )
        server = db.create_server(session, user, new_server)
        return ServerLogin(username=server.id, password=password.get_secret_value())
    except ValidationError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY)


@app.get("/v1/server/list/my", response_model=list[ServerRead])
def server_list_my(
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    return user.servers


@app.get("/v1/server/list/online", response_model=list[ServerRead])
def server_list_online(
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    return db.get_online_servers(
        session,
        cutoff=datetime.utcnow() - config.server_online_cutoff,
    )


@app.post("/v1/server/update", response_model=ServerRead)
def server_update(
    server_update: ServerUpdate,
    *,
    session: Session = Depends(db.get_session),
    server: ServerLogin = Depends(auth.auth_server),
):
    return db.update_server(session, server, server_update)
