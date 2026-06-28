# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN groupadd --system watchpoint \
    && useradd --system --gid watchpoint --home-dir /app watchpoint

COPY --from=builder /opt/venv /opt/venv
COPY migrations ./migrations
COPY watchpoint ./watchpoint

RUN mkdir -p /app/instance \
    && chown -R watchpoint:watchpoint /app/instance

USER watchpoint

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "--no-control-socket", "watchpoint:create_app()"]
