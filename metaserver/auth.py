from datetime import datetime
import hashlib
import os
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError

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


def auth_user(credentials: HTTPBasicCredentials = Depends(security)) -> Optional[User]:
    user = db.get_user_by_username(credentials.username)
    supplied_key = hash_password(credentials.password, user.salt)
    if secrets.compare_digest(supplied_key, user.key):
        return user
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )


def register_user(username: str, password: SecretStr):
    salt = secrets.token_hex(8)
    key = hash_password(password.get_secret_value(), salt)
    new_user = User(
        username=username,
        key=key,
        salt=salt,
        created=datetime.now(),
    )
    try:
        db.create_user(new_user)
    except IntegrityError:
        # Most likely the username is taken.
        raise HTTPException(status.HTTP_409_CONFLICT)
