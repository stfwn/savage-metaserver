import hashlib
import os
import secrets
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import SecretStr
from sqlmodel import Session

from metaserver.database.models import User
import metaserver.database.api as db

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
        return user
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )
