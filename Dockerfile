# syntax=docker/dockerfile:1
FROM python:3.12-slim

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt


COPY bot/ /app/bot
COPY servers/ /app/servers

CMD ["python", "-m", "bot"]
