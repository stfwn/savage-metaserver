FROM python:3.10-bullseye
WORKDIR /metaserver
COPY ./requirements.txt /metaserver/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /metaserver/requirements.txt
