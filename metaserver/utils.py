from pydantic import HttpUrl


class HttpsUrl(HttpUrl):
    allowed_schemes = {"https"}
