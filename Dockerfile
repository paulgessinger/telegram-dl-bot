FROM python:3.8-buster

WORKDIR /app

COPY src src
COPY poetry.lock .
COPY pyproject.toml .
COPY poetry.toml .

RUN pip install --no-cache-dir poetry \
    && poetry install \
    && poetry cache clear pypi --all -n


CMD [ "/app/.venv/bin/telegram-dl-bot" ]