from hashlib import sha256
import os

from fastapi import FastAPI, Depends

import metaserver.database.api as db
from metaserver.database import models
from metaserver import auth

app = FastAPI()


@app.on_event("startup")
def on_startup():
    db.init()


@app.get("/")
async def index():
    return "OK"


@app.post("/v1/user/login", response_model=bool)
async def user_login(user: models.UserLogin = Depends(auth.auth_user)):
    """Verify user credentials."""
    return


@app.post("/v1/user/register")
async def user_register(new_user: models.UserLogin):
    """Register a new user."""
    auth.register_user(new_user.username, new_user.password)
