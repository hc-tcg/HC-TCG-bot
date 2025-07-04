# syntax=docker/dockerfile:1
FROM python:3.12-slim

ARG VERSION_TAG
ENV VERSION=$VERSION_TAG

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt


COPY bot/ /app/bot
COPY resources/ /app/resources

CMD ["python", "-u", "-m", "bot"]
