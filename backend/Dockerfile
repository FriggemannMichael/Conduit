FROM python:3.6-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

ENV VIRTUAL_ENV=/opt/venv

COPY requirements.txt .
RUN uv venv "${VIRTUAL_ENV}" && uv pip install -r requirements.txt

# Runtime stage: only the virtual environment and the application code
FROM python:3.6-slim

ENV VIRTUAL_ENV=/opt/venv \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=conduit.settings \
    APP_PORT=8000
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN useradd --create-home appuser \
    && mkdir /app \
    && chown appuser:appuser /app

WORKDIR /app

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE ${APP_PORT}

CMD ["sh", "-c", "exec gunicorn conduit.wsgi:application --bind 0.0.0.0:${APP_PORT}"]
