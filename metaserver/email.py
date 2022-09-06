import logging
import secrets
import time

import boto3
from botocore.exceptions import ClientError
from cachetools import TTLCache, cached
import requests

from metaserver import constants
import metaserver.database.api as db

# Create a new SES resource and specify a region.
ses = boto3.client("ses", region_name="eu-central-1")


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
