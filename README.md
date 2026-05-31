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

## How to run

1. Create a virtual environment and install dependencies:

```sh
python -m venv venv
pip install -r requirements.txt
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

4. Run the app in development server:

```sh
flask --app watchpoint/app.py run
```
