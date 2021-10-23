FROM python:3.8-slim-buster

RUN mkdir /app

COPY nfl-bot /app

WORKDIR /app

RUN pip install -U pip && \
    pip --no-cache-dir install -r requirements.txt

CMD [ "python", "main.py" ]