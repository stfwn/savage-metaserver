import re
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    NonNegativeInt,
    SecretStr,
    ValidationError,
    constr,
    validator,
)

from metaserver import email, utils

########
# User #
########


class UserRead(BaseModel):
    """Object that is returned when the outside world asks for a user. This is
    safe to return to anyone."""

    id: int
    display_name: str
    created: datetime


class UserReadWithProof(BaseModel):
    """Object that is returned when a user logs in. Only return this to users
    that are authorized as the user that this object refers to."""

    id: int
    display_name: str
    created: datetime
    proof: str


class UserCreate(BaseModel):
    """User object that is posted to register a new user."""

    username: EmailStr
    display_name: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=8, max_length=32)

    @validator("username", pre=True, always=False)
    def validate_username(cls, val):
        if val.split("@")[-1] in email.domain_blacklist:
            raise mail.DomainBlackListError("Username mail domain is in blacklist")
        return val


class UserLogin(BaseModel):
    """User object that is posted to login."""

    username: EmailStr
    password: SecretStr = Field(min_length=8, max_length=32)


########
# Clan #
########


class ClanCreate(BaseModel):
    """Clan object when the outside world wants to create a new clan."""

    tag: constr(strip_whitespace=True, max_length=20)
    name: constr(strip_whitespace=True, max_length=100)

    @validator("tag", pre=True, always=False)
    def validate_tag(cls, v):
        max_colors = 4
        max_letters = 4

        v = v.strip()

        assert v.replace(
            "^", ""
        ).isalnum(), "Only ascii letters, numbers and '^' allowed"
        assert re.match(
            r"^(?!.*\^(?![\d]{3})).*$", v
        ), "'^' must always be followed by exactly three numbers"
        assert v.count("^") <= max_colors, "Clan tags can contain at most 4 colors"
        assert (
            len(re.sub(r"\^[\d]{3}", "", v)) <= max_letters
        ), "Clan tags can contain at most 4 letters"
        return v


##########
# Server #
##########


class ServerLogin(BaseModel):
    username: str = Field(min_length=1, max_length=8)
    password: SecretStr = Field(min_length=32, max_length=32)

    class Config:
        json_encoders = {SecretStr: lambda v: v.get_secret_value() if v else None}


class ServerCreate(BaseModel):
    host_name: utils.HttpsUrl | IPv4Address | IPv6Address
    display_name: constr(strip_whitespace=True, max_length=100)
    description: Optional[constr(strip_whitespace=True, max_length=200)]
    game_type: constr(strip_whitespace=True, max_length=10)
    max_player_count: NonNegativeInt


class ServerUpdate(ServerCreate):
    current_map: str
    current_player_count: NonNegativeInt

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, "updated", datetime.utcnow())


class ServerRead(ServerCreate):
    id: int
    current_map: str
    current_player_count: NonNegativeInt
    updated: Optional[datetime]
