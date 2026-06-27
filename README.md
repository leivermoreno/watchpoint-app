# WATCHPOINT

A simple web app to track movies and TV shows, manage your watchlist, and share reviews.

## Features

- **Search titles:** Instantly find movies and shows with autocomplete.
- **Title details:** View info, ratings, genres, streaming sources, and trailers.
- **Watchlist:** Add titles to custom lists (pending, completed, favorites).
- **User reviews:** Write, edit, and rate reviews for any title.
- **Community reviews:** Browse, sort, and vote on reviews from other users.
- **Authentication:** Sign up, log in, and manage your account securely.
- **Responsive UI:** Clean, mobile-friendly design using Bootstrap.

## Tech Stack

- Python, Flask
- PostgreSQL, SQLAlchemy
- Bootstrap 5

### Database compatibility

Watchpoint requires PostgreSQL. Although database access uses SQLAlchemy, the
application is not database-portable: review, vote, and watchlist writes use
PostgreSQL-specific `INSERT ... ON CONFLICT` upserts, and title/search cache
storage uses PostgreSQL `JSONB`. Supporting another database would require code
and schema changes.

## How to run

1. Create a virtual environment and install dependencies:

```sh
python -m venv venv
pip install -r requirements.txt
```

For development tooling, install the dev requirements instead:

```sh
pip install -r requirements-dev.txt
```

2. Create the PostgreSQL role and database:

- Create a `watchpoint` role **with a password**.

- Create a `watchpoint` database owned by that role.

3. Set the required environment variables. **All three are required**:

```sh
export WATCHPOINT_SECRET_KEY=<your-secret-key>
export WATCHPOINT_DATABASE_URI=<your-database-uri>
export WATCHPOINT_WATCHMODE_API_KEY=<your-api-key>
```

`WATCHPOINT_DATABASE_URI` is a standard SQLAlchemy/PostgreSQL DSN over TCP:

```
postgresql+psycopg2://watchpoint:<password>@<host>:5432/watchpoint?sslmode=<mode>
```

> **Note:** Always set `sslmode` to `require` at minimum so the connection is encrypted.

For local development you can copy `.env.example` to `.env` and fill in the values
— the app loads `.env` automatically via [python-dotenv](https://pypi.org/project/python-dotenv/).

4. Apply database migrations:

```sh
flask --app watchpoint db upgrade
```

For an existing database that already matches the current schema, baseline it
once instead:

```sh
flask --app watchpoint db stamp head
```

Only use `stamp head` when the existing schema matches the current migration
head.

5. Run the app in development server:

```sh
flask --app watchpoint run
```

For production, serve the factory with a WSGI server, e.g.:

```sh
gunicorn 'watchpoint:create_app()'
```

## Development checks

Tests are run with pytest:

```sh
python -m pytest
python -m pytest tests/test_auth_utils.py
python -m pytest tests/test_auth_utils.py::test_normalize_next_url_accepts_safe_relative_url
```

PostgreSQL integration tests use a separate throwaway database. Create it once:

```sh
createdb -O watchpoint watchpoint_test
```

Then set the test database URI and destructive-test opt-in before running pytest:

```sh
export WATCHPOINT_TEST_DATABASE_URI=postgresql+psycopg2://watchpoint:<password>@localhost:5432/watchpoint_test
export WATCHPOINT_ALLOW_DESTRUCTIVE_TESTS=1
```

The test database name must be `watchpoint_test` or start with
`watchpoint_test_`. The integration fixture drops all tables in that database
and applies the Alembic migrations from scratch, so
`WATCHPOINT_ALLOW_DESTRUCTIVE_TESTS=1` is required as an explicit opt-in.

Ruff is used for linting, import sorting, and formatting:

```sh
ruff check .
ruff check --fix .
ruff check --select I --fix .
ruff format .
ruff format --check .
```
