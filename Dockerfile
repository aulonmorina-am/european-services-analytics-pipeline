# syntax=docker/dockerfile:1
FROM python:3.14-slim

# Pinned uv version
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /workspace

# Dependency installation layer
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Application and dbt project
COPY src ./src
COPY config ./config
COPY dbt ./dbt

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

CMD ["bash"]