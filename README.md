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

- Create a virtual environment and install dependencies:

```sh
python -m venv venv
pip install -r requirements.txt
```

- Create postgresql role and database:

  - Create watchpoint role

  - Create watchpoint database owned by watchpoint role

The configuration expects a local connection type with trust authentication for simplicity. Adjust your `pg_hba.conf`
file as needed.

Run the app in development server:

```sh
flask --app watchpoint/app.py run
```
