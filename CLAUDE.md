# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```sh
flask --app watchpoint run
```

Required env vars (see README): `WATCHPOINT_SECRET_KEY`, `WATCHPOINT_DATABASE_URI`, `WATCHPOINT_WATCHMODE_API_KEY`. None have defaults — all three are read via `os.environ[...]`, so a missing one raises `KeyError` at startup. For local dev they can live in a gitignored `.env` (loaded by `load_dotenv()` via python-dotenv; see `.env.example`). `WATCHPOINT_DATABASE_URI` is a TCP DSN of the form `postgresql+psycopg2://user:pass@host:5432/watchpoint?sslmode=require`; `app.py` sets `SQLALCHEMY_ENGINE_OPTIONS` with `pool_pre_ping`/`pool_recycle` for resilience across networked (cloud/Docker) databases.

There is currently no test suite, linter, or formatter configured.

## Architecture

Flask app organized as four blueprints under `watchpoint/`: `title`, `auth`, `watchlist`, `review`. Each blueprint folder contains `blueprint.py` (routes), `models.py` (SQLAlchemy), optional `services.py` (data access / external API), and a `templates/` folder. The top-level `watchpoint/templates/base.html` is the shared layout; per-blueprint templates extend it.

**Import layout:** `watchpoint/` is a real package (it and each blueprint folder have an `__init__.py`). Modules use package-relative imports — `from .services import ...` for siblings in the same blueprint, `from ..db import db` / `from ..auth.utils import ...` for the shared `db` or another blueprint. `create_app()` lives in `app.py` and is re-exported from `watchpoint/__init__.py`, so the app is launched by package name (`flask --app watchpoint run`) and is importable elsewhere (`from watchpoint import create_app`) by tests, scripts, and `gunicorn 'watchpoint:create_app()'`.

**Schema setup:** `create_app()` calls `db.create_all()` at startup. There is no migrations tool (no Alembic/Flask-Migrate) — schema changes to existing tables require manual DDL or dropping/recreating the database.

**External API integration (`title/services.py`):** Title data comes from the Watchmode API. On first lookup of a `title_id`, the app fetches details + streaming sources and persists the full JSON blob into the `Title.data` column (a single JSON field). Subsequent loads come from the DB — there is no cache invalidation. Autocomplete search hits Watchmode live on every request.

**Auth flow:** `auth/blueprint.py` registers a `before_app_request` hook (`load_user`) that populates `g.user` from `session["user_id"]` for every request app-wide. Route handlers read `g.user` directly; use the `login_required` decorator from `auth/utils.py` to gate views. `User.password` is a property that hashes on assignment via Werkzeug.

**Reviews & votes:** `review/services.py` uses Postgres-specific `on_conflict_do_update` (from `sqlalchemy.dialects.postgresql`) for upserts on the `title_user_review_uc` and `review_vote_uc` unique constraints — the code is not portable to other databases. `get_reviews` issues a separate aggregated vote query and attaches a non-persistent `vote_data` attribute to each `Review` instance for the template to render.

**Watchlist:** `WATCHLIST_CHOICES = ("pending", "completed", "favorites")` is defined in `watchlist/models.py` and used both as the Postgres enum type and as the allowlist validated in the route handler.
