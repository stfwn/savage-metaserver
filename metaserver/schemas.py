from datetime import datetime
import re

from pydantic import BaseModel, EmailStr, Field, SecretStr, ValidationError, validator


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


class UserLogin(BaseModel):
    """User object that is posted to login."""

    username: EmailStr
    password: SecretStr = Field(min_length=8, max_length=32)


########
# Clan #
########


class ClanCreate(BaseModel):
    """Clan object when the outside world wants to create a new clan."""

    tag: str
    name: str

    @validator("tag")
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
