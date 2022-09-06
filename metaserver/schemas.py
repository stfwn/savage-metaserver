import base64
import binascii
from datetime import datetime
import io
from ipaddress import IPv4Address, IPv6Address
import re
from typing import Optional

from PIL import Image
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
    last_online: Optional[datetime]


class UserReadWithProof(UserRead):
    """Object that is returned when a user logs in. Only return this to users
    that are authorized as the user that this object refers to."""

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

    icon: str  # Base64 PNG
    tag: constr(strip_whitespace=True, max_length=20)
    name: constr(strip_whitespace=True, max_length=100)

    @validator("tag", pre=True, always=False)
    def validate_tag(cls, v):
        max_letters = 4

        v = v.strip()

        assert re.match(
            r"^(?!.*\^(?!([\d]{3}|[rgbwkycm]))).*$", v
        ), "'^' must always be followed by exactly three numbers or one of 'rgbwkycm'"
        assert (
            v.count("^") <= max_letters
        ), f"Clan tags can contain at most {max_letters} colors"
        without_colors = re.sub(r"\^([\d]{3}|[rgbwkycm])", "", v)
        assert (
            len(without_colors) <= max_letters
        ), f"Clan tags can contain at most {max_letters} letters"
        return v

    @validator("icon")
    def validate_icon(cls, v):
        try:
            img_bytes = base64.b64decode(v)
            img = Image.open(io.BytesIO(img_bytes))
            img.verify()
        except (TypeError, binascii.Error, ValueError, OSError, IOError) as e:
            raise ValueError("Image could not be validated")
        if img.format.lower() != "png":
            raise ValueError("Image should be in PNG format")
        if img.size[0] > 64 or img.size[1] > 64:
            raise ValueError("Image is too large")
        if img.size[0] != img.size[1]:
            raise ValueError("Image should be square")
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
    port: int
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
    current_map: constr(max_length=100)
    current_player_count: NonNegativeInt
    updated: Optional[datetime]
