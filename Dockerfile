FROM python:3.10.7-alpine3.16
RUN apk add bash
WORKDIR /metaserver
COPY ./requirements.txt /metaserver/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /metaserver/requirements.txt
