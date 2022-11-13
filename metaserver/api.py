from datetime import datetime
import base64
from itertools import chain
import json
import secrets

from fastapi import (
    BackgroundTasks,
    Body,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from pydantic import Field, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

import metaserver.database.api as db
from metaserver import auth, config, email
from metaserver.database.models import (
    Clan,
    EmailToken,
    Skin,
    User,
    UserClanLink,
    UserStats,
    Server,
)
from metaserver.database.utils import UserClanLinkDeletedReason, UserClanLinkRank
from metaserver import metrics
from metaserver.schemas import (
    ClanCreate,
    ClanUpdateIcon,
    MatchUpdate,
    ServerLogin,
    ServerCreate,
    ServerRead,
    ServerUpdate,
    Team,
    UserClanLinkUpdateRank,
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


@app.get("/v1/user/by-id", response_model=UserRead, tags=["user"])
def user(
    user_id: int = Query(),
    *,
    user: UserLogin = Depends(auth.auth_user),
    session: Session = Depends(db.get_session),
):
    if user := db.get_user_by_id(session, user_id):
        return user
    raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")


@app.get("/v1/user/by-id/batch", response_model=list[UserRead], tags=["user"])
def user_by_id_batch(
    user_ids: list[int] = Query(),
    *,
    user: UserLogin = Depends(auth.auth_user),
    session: Session = Depends(db.get_session),
):
    return db.get_users_by_id(session, user_ids)


@app.get("/v1/user/clan-invites", response_model=list[UserClanLink], tags=["user"])
def user_clan_invites(
    *,
    user: UserLogin = Depends(auth.auth_user),
    session: Session = Depends(db.get_session),
):
    return [link for link in user.clan_links if link.is_open_invitation]


@app.post("/v1/user/login", response_model=UserReadWithProof, tags=["user"])
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


@app.post("/v1/user/verify-user-proof", response_model=bool, tags=["user"])
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


@app.post("/v1/user/register", response_model=UserReadWithProof, tags=["user"])
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
        user = db.commit_and_refresh(session, user)
        email_token = EmailToken(user=user)
        db.commit_and_refresh(session, email_token)
        email.send_verification_email(recipient=user.username, token=email_token.key)
    except IntegrityError as e:
        if "display_name" in e._message():
            raise HTTPException(status.HTTP_409_CONFLICT, "Display name taken")
        else:
            raise HTTPException(status.HTTP_409_CONFLICT, "Username taken")
    return UserReadWithProof(**user.dict(), proof=auth.generate_user_proof(user.id))


@app.post("/v1/user/verify-clan-membership", response_model=bool, tags=["user"])
def user_verify_clan_membership(
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if link := db.get_user_clan_link(session, user.id, clan_id):
        return link.is_membership
    return False


@app.post("/v1/user/email/verify", response_model=UserReadWithProof, tags=["user"])
def user_email_verify(
    mail_token: str = Body(embed=True, min_length=6, max_length=6),
    *,
    background_tasks: BackgroundTasks,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_unverified_user),
):
    if user.verified_email:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User already verified mail")

    if token := user.email_token:
        if secrets.compare_digest(mail_token, token.key):
            user.verified_email = datetime.utcnow()
            db.commit_and_refresh(session, user)
            background_tasks.add_task(db.set_user_last_online_now, session, user)
            return UserReadWithProof(
                **user.dict(), proof=auth.generate_user_proof(user.id)
            )
        else:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Incorrect mail verification token"
            )
    else:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No mail verification token found for user (request a new one)",
        )


@app.post("/v1/user/email/renew-token", tags=["user"])
def user_email_new_token(
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_unverified_user),
):
    if user.verified_email:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User already verified mail")
    if email_token := user.email_token:
        if datetime.utcnow() - email_token.created <= config.email_token_renew_timeout:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Wait at least {config.email_token_renew_timeout.seconds} seconds before requesting a new token",
            )
        email_token.key = EmailToken.new_key()
        db.commit_and_refresh(session, email_token)
        email.send_verification_email(user.username, email_token.key)
    return "Token sent"


@app.post("/v1/user/change-display-name", response_model=UserRead, tags=["user"])
def user_change_display_name(
    display_name: str = Body(embed=True, min_length=1, max_length=64),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    user.display_name = display_name
    return db.commit_and_refresh(session, user)


@app.get("/v1/user/stats", response_model=UserStats, tags=["user"])
def get_user_stats(
    user_id: int = Query(),
    server_id: int = Query(),
    *,
    session: Session = Depends(db.get_session),
    _: UserLogin | ServerLogin = Depends(auth.auth_user_or_server),
):
    if user_stats := db.get_user_stats(session, user_id, server_id):
        return user_stats
    raise HTTPException(status.HTTP_404_NOT_FOUND)


@app.get("/v1/user/stats/batch", response_model=list[UserStats], tags=["user"])
def get_user_stats(
    user_ids: int = Query(),
    server_id: int = Query(),
    *,
    session: Session = Depends(db.get_session),
    _: UserLogin | ServerLogin = Depends(auth.auth_user_or_server),
):
    return db.get_user_stats_batch(session, user_id, server_id)


############
# /v1/clan #
############


@app.get("/v1/clan/all", response_model=list[Clan], tags=["clan"])
def clan(
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    return db.get_all_clans(session)


@app.get(
    "/v1/clan/icon/{clan_id}.png",
    responses={200: {"content": {"image/png": {}}}},
    response_class=Response,
    tags=["clan"],
)
def get_clan_icon_png(clan_id: int, session: Session = Depends(db.get_session)):
    if clan := db.get_clan_by_id(session, clan_id):
        return Response(content=base64.b64decode(clan.icon), media_type="image/png")
    raise HTTPException(status.HTTP_404_NOT_FOUND)


@app.get("/v1/clan/by-id", response_model=Clan, tags=["clan"])
def clan_by_id(
    clan_id: int,
    *,
    session: Session = Depends(db.get_session),
    _: UserLogin | ServerLogin = Depends(auth.auth_user_or_server),
):
    if clan := db.get_clan_by_id(session, clan_id):
        return clan
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Clan not found")


@app.get("/v1/clan/by-id/batch", response_model=list[Clan], tags=["clan"])
def clan_by_id_batch(
    clan_ids: list[int] = Query(),
    *,
    _: UserLogin | ServerLogin = Depends(auth.auth_user_or_server),
    session: Session = Depends(db.get_session),
):
    return db.get_clans_by_id(session, clan_ids)


@app.get("/v1/clan/for-user/by-id", response_model=list[UserClanLink], tags=["clan"])
def clan_for_user_by_id(
    user_id: int,
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if user_id != user.id:
        if not (user := db.get_user_by_id(session, user_id)):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return [link for link in user.clan_links if link.is_membership]


@app.post("/v1/clan/invite", tags=["clan"])
def clan_invite(
    user_id: int = Body(embed=True),
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if not (inviter_clan_link := db.get_user_clan_link(session, user.id, clan_id)):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Clan doesn't exist or inviter isn't in it",
        )
    if not (inviter_clan_link.rank >= UserClanLinkRank.ADMIN):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Inviter is not clan admin",
        )
    if not (invitee := db.get_user_by_id(session, user_id)):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Invitee doesn't exist",
        )
    ucl = UserClanLink(user=invitee, clan=inviter_clan_link.clan)
    try:
        db.commit_and_refresh(session, ucl)
    except IntegrityError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Invitee has an existing relation to clan (invited/member/left/kicked)",
        )


@app.post("/v1/clan/invite-response", tags=["clan"])
def clan_invite_response(
    clan_id: int = Body(embed=True),
    accept: bool = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    """For `accept`, supply `1` or `true` to accept, `0` or `false` to decline."""
    if link := db.get_user_clan_link(session, user.id, clan_id):
        if link.is_open_invitation:
            if accept:
                link.joined = datetime.utcnow()
                db.commit_and_refresh(session, link)
                return
            else:
                link.deleted = datetime.utcnow()
                link.deleted_reason = UserClanLinkDeletedReason.DECLINED
                db.commit_and_refresh(session, link)
        elif link.is_declined_invitation:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "User previously declined this invitation",
            )
        elif link.is_retracted_invitation:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "This invitation has been retracted",
            )
        elif link.is_membership:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "User is already a member of clan",
            )
        elif link.user_left_clan:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "User has left clan and was not reinvited",
            )
        elif link.user_was_kicked:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "User was kicked from clan and was not reinvited",
            )
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY, "User is not invited to join clan"
    )


@app.post("/v1/clan/kick", tags=["clan"])
def clan_kick(
    clan_id: int = Body(embed=True),
    user_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if not (object_link := db.get_user_clan_link(session, user.id, clan_id)):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Clan doesn't exist or user is not in it.",
        )
    if not (subject_link := db.get_user_clan_link(session, user_id, clan_id)):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Clan doesn't exist or user is not in it.",
        )

    if (
        object_link := db.get_user_clan_link(session, user.id, clan_id)
    ) and object_link.rank >= UserClanLinkRank.ADMIN:
        member_link = db.get_user_clan_link(session, user_id, clan_id)
        if member_link.rank >= UserClanLinkRank.ADMIN:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Clan admins cannot be kicked",
            )
        member_link.deleted = datetime.utcnow()
        member_link.deleted_reason = UserClanLinkDeletedReason.KICKED
        db.commit_and_refresh(session, member_link)
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "User is not authorized to kick members of this clan",
    )


@app.get("/v1/clan/invites", response_model=list[UserClanLink], tags=["clan"])
def clan_invites(
    clan_id: int,
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if user_clan_link := db.get_user_clan_link(session, user.id, clan_id):
        return db.get_clan_user_invites(session, clan_id)
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "User is not authorized to view clan invites for this clan",
    )


@app.get("/v1/clan/members", response_model=list[UserClanLink], tags=["clan"])
def clan_members(
    clan_id: int,
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    clan = db.get_clan_by_id(session, clan_id)
    return [link for link in clan.user_links if link.is_membership]


@app.post("/v1/clan/register", response_model=Clan, tags=["clan"])
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


@app.post("/v1/clan/update-icon", response_model=Clan, tags=["clan"])
def clan_change_icon(
    clan_update: ClanUpdateIcon,
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if (
        user_clan_link := db.get_user_clan_link(session, user.id, clan_update.clan_id)
    ) and user_clan_link.rank >= UserClanLinkRank.ADMIN:
        clan = user_clan_link.clan
        clan.icon = clan_update.icon
        db.commit_and_refresh(session, clan)
        return clan
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "User is not authorized to change icon for this clan",
    )


@app.post("/v1/clan/update-rank", response_model=UserClanLink, tags=["clan"])
def clan_update_rank(
    update: UserClanLinkUpdateRank,
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    if not (object_link := db.get_user_clan_link(session, user.id, update.clan_id)):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Clan doesn't exist or modifying user is not in it.",
        )
    if not (
        subject_link := db.get_user_clan_link(session, update.user_id, update.clan_id)
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Clan doesn't exist or subject user is not in it.",
        )

    object_rank = UserClanLinkRank(object_link.rank)

    if object_rank <= subject_link.rank:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Modifying user does not outrank subject user.",
        )
    if update.rank > object_rank:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "New rank is above the modifying user's rank.",
        )
    subject_link.rank = update.rank
    return db.commit_and_refresh(session, subject_link)


############
# /v1/skin #
############


@app.get("/v1/skin/for-user/by-id", response_model=list[Skin], tags=["skin"])
def skin_for_user_by_id(
    user_id: int = Query(),
    clan_id: int | None = Query(None),
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    skins = db.get_skins_for_user_by_id(session, user_id)
    if clan_id:
        skins += db.get_skins_for_clan_by_id(session, clan_id)
    return skins


@app.get("/v1/skin/for-clan/by-id", response_model=list[Skin], tags=["skin"])
def skin_for_clan_by_id(
    clan_id: int,
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    return db.get_skins_for_clan_by_id(session, clan_id)


##############
# /v1/server #
##############


@app.post("/v1/server/register", response_model=ServerLogin, tags=["server"])
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


@app.get("/v1/server/list/my", response_model=list[ServerRead], tags=["server"])
def server_list_my(
    *,
    session: Session = Depends(db.get_session),
    user: UserLogin = Depends(auth.auth_user),
):
    return user.servers


@app.get("/v1/server/list/online", response_model=list[ServerRead], tags=["server"])
def server_list_online(*, session: Session = Depends(db.get_session)):
    return db.get_online_servers(
        session,
        cutoff=datetime.utcnow() - config.server_online_cutoff,
    )


@app.post("/v1/server/update", response_model=ServerRead, tags=["server"])
def server_update(
    server_update: ServerUpdate,
    *,
    session: Session = Depends(db.get_session),
    server: ServerLogin = Depends(auth.auth_server),
):
    return db.update_server(session, server, server_update)


@app.post("/v1/server/verify-clan-membership", response_model=bool, tags=["server"])
def server_verify_clan_membership(
    user_id: int = Body(embed=True),
    clan_id: int = Body(embed=True),
    *,
    session: Session = Depends(db.get_session),
    server: ServerLogin = Depends(auth.auth_server),
):
    if link := db.get_user_clan_link(session, user_id, clan_id):
        return link.is_membership
    return False


@app.post("/v1/server/match-update", tags=["server"])
def server_match_update(
    match_update: MatchUpdate,
    *,
    session: Session = Depends(db.get_session),
    server: ServerLogin = Depends(auth.auth_server),
):
    """Post a match update to update stats per player for this server. The
    match update data itself is not stored (yet)."""
    user_stats_per_team = {
        team.id: db.get_user_stats_batch(
            session,
            [fp.user_id for fp in team.field_players],
            server.id,
        )
        for team in match_update.teams
    }

    for team_id, users_stats in user_stats_per_team.items():
        new_users = [
            set([us.user_id for us in team.field_players])
            for team in match_update.teams
            if team.id == team_id
        ][0] - set([us.user_id for us in users_stats])
        new_stats_to_commit = []
        for user_id in new_users:
            new_stats = UserStats(user_id=user_id, server_id=server.id)
            user_stats_per_team[team_id].append(new_stats)
            # Game server may use 0 or < 0 for unregistered users.
            if user_id > 0:
                new_stats_to_commit.append(new_stats)
        db.commit_and_refresh_batch(session, new_stats_to_commit)

    mean_rating_per_team = {
        team_id: metrics.mean_skill_rating(us)
        for team_id, us in user_stats_per_team.items()
    }
    for team_id, user_stats in user_stats_per_team.items():
        for us in user_stats:
            us.skill_rating = metrics.skill_rating(
                current_rating=us.skill_rating,
                mean_team_rating=mean_rating_per_team[team_id],
                mean_opponent_rating=(
                    mean_rating_per_team[match_update.winner]
                    if match_update.winner != -1
                    else sum(
                        [m for tid, m in mean_rating_per_team.items() if tid != team_id]
                    )
                    / (len(match_update.teams) - 1)
                ),
                achieved_score=(
                    (team_id == match_update.winner)
                    if match_update.winner != -1
                    else 0.5
                ),
            )
            us.last_seen = datetime.utcnow()
            us.matches_played += 1
        db.commit_and_refresh_batch(
            session, [us for us in user_stats if us.user_id > 0]
        )
