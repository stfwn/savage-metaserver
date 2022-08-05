import hashlib
import os
import secrets
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import SecretStr
from sqlmodel import Session

import metaserver.database.api as db
from metaserver import constants
from metaserver.database.models import Server, User

security = HTTPBasic()


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=10_000,
    ).hex()


def new_password(password: SecretStr):
    salt = secrets.token_hex(8)
    key = hash_password(password.get_secret_value(), salt)
    return key, salt


def auth_user(
    session: Session = Depends(db.get_session),
    credentials: HTTPBasicCredentials = Depends(security),
) -> User:
    user = db.get_user_by_username(session, credentials.username)
    supplied_key = hash_password(credentials.password, user.salt)
    if secrets.compare_digest(supplied_key, user.key):
        if not user.verified_email:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail="User email is unverified",
                headers={"WWW-Authenticate": "Basic"},
            )
        return user
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )


def auth_unverified_user(
    session: Session = Depends(db.get_session),
    credentials: HTTPBasicCredentials = Depends(security),
) -> User:
    user = db.get_user_by_username(session, credentials.username)
    supplied_key = hash_password(credentials.password, user.salt)
    if secrets.compare_digest(supplied_key, user.key):
        return user
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )


def auth_server(
    session: Session = Depends(db.get_session),
    credentials: HTTPBasicCredentials = Depends(security),
) -> Server:
    server = db.get_server_by_id(session, credentials.username)
    supplied_key = hash_password(credentials.password, server.salt)
    if secrets.compare_digest(supplied_key, server.key):
        return server
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )


def generate_user_proof(user_id: int) -> str:
    return hashlib.sha256(
        (
            # Proofs are specific to users.
            str(user_id)
            # Only the server can generate proofs and proofs invalidate on restart.
            + constants.secret_for_user_proof
            # Proofs invalidate every day at 00:00 UTC.
            + datetime.utcnow().strftime("%Y-%m-%d")
        ).encode("utf-8")
    ).hexdigest()


def verify_user_proof(user_id: int, user_proof: str) -> bool:
    return secrets.compare_digest(user_proof, generate_user_proof(user_id))


def generate_server_password() -> SecretStr:
    # 16 bytes -> 32 hex chars.
    return SecretStr(secrets.token_hex(16))
