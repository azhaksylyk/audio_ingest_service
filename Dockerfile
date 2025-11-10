FROM python:3.11-slim
WORKDIR /code

# Install system libs required for soundfile + PostgreSQL driver
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* /code/
RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root

COPY . /code