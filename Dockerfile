FROM python:3.11.3

RUN pip install poetry

COPY ./pyproject.toml /app/pyproject.toml
COPY ./poetry.lock /app/poetry.lock

WORKDIR /app

RUN poetry install

COPY . /app/.
