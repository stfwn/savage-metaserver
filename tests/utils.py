from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import select

from metaserver import email
import metaserver.database.api as db
from metaserver.database.models import EmailToken


def dict_without_key(d, k):
    d2 = d.copy()
    del d2[k]
    return d2


def register_user(client: TestClient, display_name: str, username: str, password: str):
    user = client.post(
        "/v1/user/register",
        json=dict(username=username, display_name=display_name, password=password),
    ).json()

    session = next(db.get_session())
    mail_token = (
        session.exec(select(EmailToken).where(EmailToken.user_id == user["id"]))
        .one()
        .key
    )

    user = client.post(
        "/v1/user/email/verify",
        json=dict(mail_token=mail_token),
        auth=(username, password),
    ).json()

    # Add credentials for testing purposes.
    user["auth"] = (username, password)
    return user


def get_email_token_for_user_id(user_id: int):
    session = next(db.get_session())
    return (
        session.exec(select(EmailToken).where(EmailToken.user_id == user_id)).one().key
    )


def set_email_token_created_for_user_id_to_last_year(user_id: int):
    session = next(db.get_session())
    email_token = session.exec(
        select(EmailToken).where(EmailToken.user_id == user_id)
    ).one()
    email_token.created = datetime.utcnow() - timedelta(days=365)
    db.commit_and_refresh(session, email_token)
