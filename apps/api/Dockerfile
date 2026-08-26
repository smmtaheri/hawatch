FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    DJANGO_SETTINGS_MODULE=hawatch.config.settings.local \
    GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so \
    GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gdal-bin \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
        libpq-dev \
        postgresql-client \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.8.4 /uv /usr/local/bin/uv

WORKDIR /opt/deps
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --group dev

WORKDIR /app
COPY . .
RUN chmod +x entrypoint.sh

ENV VIRTUAL_ENV=/opt/deps/.venv \
    PATH="/opt/deps/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
