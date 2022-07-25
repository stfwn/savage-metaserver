import logging
import secrets
import time

import boto3
from botocore.exceptions import ClientError
from cachetools import TTLCache, cached
import requests

from metaserver import constants

# Create a new SES resource and specify a region.
ses = boto3.client("ses", region_name="eu-central-1")

CACHE_TTL = 60 * 5
TOKEN_CACHE = TTLCache(maxsize=10_000, ttl=CACHE_TTL)
TOKEN_CACHE_REVERSE = TTLCache(maxsize=10_000, ttl=CACHE_TTL)
GENERATION_TIME_FOR_USER_ID = TTLCache(maxsize=10_000, ttl=CACHE_TTL)


class DomainBlacklist:
    def __contains__(self, key):
        return key in self.blacklist()

    @cached(TTLCache(maxsize=1, ttl=60 * 60 * 24))
    def blacklist(self):
        return set(
            requests.get(constants.disposable_email_domains_url).text.split("\n")
        )


class DomainBlackListError(ValueError):
    pass


domain_blacklist = DomainBlacklist()


def generate_token(user_id: int) -> str:
    # Invalidate old token if applicable
    try:
        old_token = TOKEN_CACHE_REVERSE[user_id]
        del TOKEN_CACHE[old_token]
        del TOKEN_CACHE_REVERSE[user_id]
    except KeyError:
        pass

    # Generate new token
    token = secrets.token_urlsafe(4)  # 4 bytes -> token has length 6
    TOKEN_CACHE[token] = user_id
    TOKEN_CACHE_REVERSE[user_id] = token
    GENERATION_TIME_FOR_USER_ID[user_id] = time.monotonic()
    return token


def verify_token(user_id: int, token: str) -> bool:
    return TOKEN_CACHE[token] == user_id


def get_user_id_for_verification_token(token: str) -> int:
    user_id = TOKEN_CACHE[token]
    return user_id


def get_token_age_for_user(user_id: int) -> int:
    """Get how long ago a token was generated in seconds."""
    return int(time.monotonic() - GENERATION_TIME_FOR_USER_ID[user_id])


def send_verification_email(recipient: str, token: str):
    charset = "UTF-8"
    sender = "Savage Community Server <noreply@community-server.info>"
    subject = "Email Verification for the Savage Community Server"

    # The email body for recipients with non-HTML email clients.
    body_text = (
        "Savage Community Server\n"
        "Verify your email by entering the following code in the in-game verification box.\n"
        f"{token}\n"
        "See you on the field!\n"
        "Kind regards,\n"
        "The Savage Community Server team"
    )

    # The HTML body of the email.
    body_html = f"""<html>
    <head>
    </head>
    <body>
        <h1>Savage Community Server</h1>
        <p>Verify your email by entering the following code in the in-game verification box.</p>
        <h2>{token}</h2>
        <p>See you on the field!</p>
        <p>Kind regards,<p>
        <p>The Savage Community Server team.</p>
    </body>
    </html>"""

    try:
        response = ses.send_email(
            Destination={
                "ToAddresses": [
                    recipient,
                ],
            },
            Message={
                "Body": {
                    "Html": {
                        "Charset": charset,
                        "Data": body_html,
                    },
                    "Text": {
                        "Charset": charset,
                        "Data": body_text,
                    },
                },
                "Subject": {
                    "Charset": charset,
                    "Data": subject,
                },
            },
            Source=sender,
        )
    except ClientError as e:
        logging.log(logging.ERROR, e.response["Error"]["Message"])
    else:
        logging.log(logging.DEBUG, "Sent email with ID: " + str(response["MessageId"]))
