import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from flask import g
from flask_migrate import upgrade as alembic_upgrade
from sqlalchemy import MetaData, func, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from watchpoint import create_app
from watchpoint.auth.models import User
from watchpoint.db import db
from watchpoint.review import services as review_services
from watchpoint.review.models import Review, Vote
from watchpoint.title import services as title_services
from watchpoint.title.models import Title, TitleSearchCache
from watchpoint.watchlist import services as watchlist_services
from watchpoint.watchlist.models import Watchlist

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
DESTRUCTIVE_TEST_OPT_IN_ENV = "WATCHPOINT_ALLOW_DESTRUCTIVE_TESTS"
TEST_DATABASE_NAME_RE = re.compile(r"^watchpoint_test(?:_[a-z0-9]+)*$")


def is_safe_postgresql_test_database_name(database):
    return TEST_DATABASE_NAME_RE.fullmatch((database or "").lower()) is not None


@pytest.mark.parametrize(
    "database",
    [
        "watchpoint_test",
        "watchpoint_test_local",
        "watchpoint_test_ci_42",
        "WATCHPOINT_TEST_CI",
    ],
)
def test_postgresql_database_name_guard_accepts_dedicated_watchpoint_test_names(
    database,
):
    assert is_safe_postgresql_test_database_name(database)


@pytest.mark.parametrize(
    "database",
    [
        None,
        "",
        "contest",
        "latest",
        "my_test",
        "test_watchpoint",
        "watchpoint",
        "watchpoint_testing",
        "watchpoint_test-1",
        "watchpoint_test_",
        "watchpoint_test__local",
    ],
)
def test_postgresql_database_name_guard_rejects_ambiguous_database_names(database):
    assert not is_safe_postgresql_test_database_name(database)


def title_payload(title_id, title, **overrides):
    payload = {
        "id": title_id,
        "title": title,
        "type": "movie",
        "year": 1995,
        "sources": [{"name": "Kanopy", "region": "US"}],
    }
    payload.update(overrides)
    return payload


def uri_with_non_utc_session_timezone(uri):
    url = make_url(uri).update_query_dict({"options": "-c timezone=America/New_York"})
    return url.render_as_string(hide_password=False)


@pytest.fixture
def postgresql_test_database_uri():
    uri = os.environ.get("WATCHPOINT_TEST_DATABASE_URI")
    if not uri:
        pytest.fail(
            "Set WATCHPOINT_TEST_DATABASE_URI to run required PostgreSQL "
            "integration tests.",
            pytrace=False,
        )

    url = make_url(uri)
    if not url.drivername.startswith("postgresql"):
        pytest.fail(
            "WATCHPOINT_TEST_DATABASE_URI must use a PostgreSQL driver.",
            pytrace=False,
        )

    if os.environ.get(DESTRUCTIVE_TEST_OPT_IN_ENV) != "1":
        pytest.fail(
            f"Set {DESTRUCTIVE_TEST_OPT_IN_ENV}=1 to run PostgreSQL integration "
            "tests that drop all tables in WATCHPOINT_TEST_DATABASE_URI.",
            pytrace=False,
        )

    database = (url.database or "").lower()
    if not is_safe_postgresql_test_database_name(database):
        pytest.fail(
            "WATCHPOINT_TEST_DATABASE_URI must point to a dedicated test database "
            "named watchpoint_test or watchpoint_test_<suffix> because these tests "
            "drop and migrate tables."
        )

    return uri


def drop_reflected_tables():
    db.session.remove()
    metadata = MetaData()
    metadata.reflect(bind=db.engine)
    metadata.drop_all(bind=db.engine)


@pytest.fixture
def integration_app(monkeypatch, postgresql_test_database_uri):
    monkeypatch.setenv("WATCHPOINT_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv(
        "WATCHPOINT_DATABASE_URI",
        uri_with_non_utc_session_timezone(postgresql_test_database_uri),
    )
    monkeypatch.setenv("WATCHPOINT_WATCHMODE_API_KEY", "test-api-key")

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.app_context():
        try:
            db.session.execute(text("SELECT 1"))
        except OperationalError as exc:
            pytest.fail(
                f"PostgreSQL test database is unavailable: {exc.orig}",
                pytrace=False,
            )
        db.session.rollback()

        drop_reflected_tables()
        alembic_upgrade(directory=str(MIGRATIONS_DIR))

    yield app

    with app.app_context():
        drop_reflected_tables()
        db.engine.dispose()


def test_postgresql_connection_timezone_is_utc(integration_app):
    with integration_app.app_context():
        session_timezone = db.session.scalar(text("SHOW timezone"))
        db_now = db.session.scalar(select(func.now()))

        assert session_timezone == "UTC"
        assert db_now.tzinfo is not None
        assert db_now.utcoffset() == timedelta(0)


def create_user(nickname, password="correct horse battery staple"):
    user = User(nickname=nickname)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user.id


def create_review_row(title_id, user_id, comment, stars=4, created_at=None):
    review = Review(
        title_id=title_id,
        user_id=user_id,
        comment=comment,
        stars=stars,
    )
    if created_at is not None:
        review.created_at = created_at
    db.session.add(review)
    db.session.commit()
    return review.id


def test_auth_signup_and_login_use_real_app_and_database(integration_app):
    client = integration_app.test_client()

    signup_response = client.post(
        "/auth/signup",
        data={"nickname": "cinephile", "password": "long-enough-password"},
    )

    assert signup_response.status_code == 302
    assert urlsplit(signup_response.headers["Location"]).path == "/auth/login"

    with integration_app.app_context():
        user = db.session.scalar(select(User).where(User.nickname == "cinephile"))
        assert user is not None
        assert user.check_password("long-enough-password")
        assert "long-enough-password" not in user._password
        user_id = user.id

    login_response = client.post(
        "/auth/login",
        data={"nickname": "cinephile", "password": "long-enough-password"},
    )

    assert login_response.status_code == 302
    assert urlsplit(login_response.headers["Location"]).path == "/"
    with client.session_transaction() as session:
        assert session["user_id"] == user_id


def test_title_and_search_cache_upserts_update_existing_rows(integration_app):
    with integration_app.app_context():
        title_services.upsert_title(title_payload(42, "Heat", year=1995))
        title = db.session.get_one(Title, 42)
        old_title_fetched_at = datetime.now(timezone.utc) - timedelta(days=30)
        title.fetched_at = old_title_fetched_at
        db.session.commit()

        title_services.upsert_title(
            title_payload(
                42,
                "Heat: Director's Cut",
                year=1996,
                sources=[{"name": "Criterion", "region": "US"}],
            )
        )

        title_rows = db.session.scalars(select(Title)).all()
        refreshed_title = db.session.get_one(Title, 42)
        assert len(title_rows) == 1
        assert refreshed_title.name == "Heat: Director's Cut"
        assert refreshed_title.year == 1996
        assert refreshed_title.data["sources"] == [
            {"name": "Criterion", "region": "US"}
        ]
        assert refreshed_title.fetched_at > old_title_fetched_at

        cache_key = title_services.autocomplete_search_cache_key("heat")
        title_services.upsert_search_cache(
            cache_key,
            [
                {
                    "id": 42,
                    "name": "Heat",
                    "image_url": "https://example.test/heat.jpg",
                }
            ],
        )
        cache = db.session.get_one(TitleSearchCache, cache_key)
        old_cache_fetched_at = datetime.now(timezone.utc) - timedelta(days=2)
        cache.fetched_at = old_cache_fetched_at
        db.session.commit()

        title_services.upsert_search_cache(
            cache_key,
            [
                {
                    "id": 42,
                    "name": "Heat: Director's Cut",
                    "image_url": "https://example.test/heat-dc.jpg",
                }
            ],
        )

        cache_rows = db.session.scalars(select(TitleSearchCache)).all()
        refreshed_cache = db.session.get_one(TitleSearchCache, cache_key)
        assert len(cache_rows) == 1
        assert refreshed_cache.results == [
            {
                "id": 42,
                "name": "Heat: Director's Cut",
                "image_url": "https://example.test/heat-dc.jpg",
            }
        ]
        assert refreshed_cache.fetched_at > old_cache_fetched_at


def test_stale_title_and_search_cache_fall_back_to_cached_rows(
    integration_app, monkeypatch
):
    with integration_app.app_context():
        title_services.upsert_title(title_payload(42, "Heat"))
        title = db.session.get_one(Title, 42)
        title.fetched_at = datetime.now(timezone.utc) - timedelta(days=30)
        db.session.commit()

        def fail_title_refresh(title_id, abort_on_error=True, fallback_sources=None):
            assert title_id == 42
            assert abort_on_error is False
            assert fallback_sources == [{"name": "Kanopy", "region": "US"}]
            return None

        monkeypatch.setattr(title_services, "get_title_data", fail_title_refresh)

        assert title_services.get_title_info_or_404("42").name == "Heat"
        assert db.session.scalar(select(func.count()).select_from(Title)) == 1

        cache_key = title_services.autocomplete_search_cache_key("heat")
        title_services.upsert_search_cache(
            cache_key,
            [
                {
                    "id": 42,
                    "name": "Heat",
                    "image_url": "https://example.test/heat.jpg",
                }
            ],
        )
        cache = db.session.get_one(TitleSearchCache, cache_key)
        cache.fetched_at = datetime.now(timezone.utc) - timedelta(days=2)
        db.session.commit()

        def fail_autocomplete(url, params, abort_on_error=True):
            assert abort_on_error is False
            assert params["search_type"] == 2
            return None

        monkeypatch.setattr(title_services, "_get_watchmode_json", fail_autocomplete)

        assert title_services.get_autocomplete_titles("Heat") == [
            {"id": 42, "name": "Heat", "image_url": "https://example.test/heat.jpg"}
        ]
        assert (
            db.session.scalar(select(func.count()).select_from(TitleSearchCache)) == 1
        )


def test_watchlist_upsert_and_remove_use_postgresql_conflict_constraint(
    integration_app,
):
    with integration_app.app_context():
        title_services.upsert_title(title_payload(42, "Heat"))
        user_id = create_user("watcher")

        with integration_app.test_request_context("/"):
            g.user = SimpleNamespace(id=user_id)
            watchlist_services.upsert_watchlist(42, "pending")
            watchlist_services.upsert_watchlist(42, "completed")

            row = db.session.scalar(select(Watchlist))
            assert row.status == "completed"
            assert db.session.scalar(select(func.count()).select_from(Watchlist)) == 1

            watchlist_services.remove_watchlist(42)

        assert db.session.scalar(select(func.count()).select_from(Watchlist)) == 0


def test_review_upsert_uses_postgresql_conflict_constraint(integration_app):
    with integration_app.app_context():
        title_services.upsert_title(title_payload(42, "Heat"))
        user_id = create_user("reviewer")

        with integration_app.test_request_context("/"):
            g.user = SimpleNamespace(id=user_id)
            review_services.upsert_review(42, "This first review is long enough.", 3)

            review = db.session.scalar(select(Review))
            assert review is not None
            old_updated_at = datetime.now(timezone.utc) - timedelta(days=1)
            review.updated_at = old_updated_at
            db.session.commit()

            review_services.upsert_review(42, "This edited review is better.", 5)

        review_rows = db.session.scalars(select(Review)).all()
        assert len(review_rows) == 1
        assert review_rows[0].comment == "This edited review is better."
        assert review_rows[0].stars == 5
        assert review_rows[0].updated_at > old_updated_at


def test_vote_toggle_inserts_deletes_and_updates_one_vote_row(integration_app):
    with integration_app.app_context():
        title_services.upsert_title(title_payload(42, "Heat"))
        author_id = create_user("author")
        voter_id = create_user("voter")
        review_id = create_review_row(42, author_id, "This review has enough detail.")

        with integration_app.test_request_context("/"):
            g.user = SimpleNamespace(id=voter_id)
            review_services.toggle_vote(review_id, True)
            assert db.session.scalar(select(func.count()).select_from(Vote)) == 1
            assert db.session.scalar(select(Vote.upvote)) is True

            review_services.toggle_vote(review_id, True)
            assert db.session.scalar(select(func.count()).select_from(Vote)) == 0

            review_services.toggle_vote(review_id, False)
            review_services.toggle_vote(review_id, True)

        vote_rows = db.session.scalars(select(Vote)).all()
        assert len(vote_rows) == 1
        assert vote_rows[0].upvote is True


def test_review_sorting_counts_and_vote_totals_use_real_queries(integration_app):
    with integration_app.app_context():
        title_services.upsert_title(title_payload(42, "Heat"))
        title_services.upsert_title(title_payload(99, "Collateral", year=2004))
        author_one_id = create_user("author-one")
        author_two_id = create_user("author-two")
        viewer_id = create_user("viewer")
        extra_voter_id = create_user("extra-voter")
        old_time = datetime.now(timezone.utc) - timedelta(days=2)
        new_time = datetime.now(timezone.utc) - timedelta(days=1)

        older_review_id = create_review_row(
            42,
            author_one_id,
            "This older Heat review has enough detail.",
            created_at=old_time,
        )
        newer_review_id = create_review_row(
            42,
            author_two_id,
            "This newer Heat review has enough detail.",
            created_at=new_time,
        )
        create_review_row(99, author_one_id, "This other review has enough detail.")

        db.session.execute(
            update(Review)
            .where(Review.id == older_review_id)
            .values(created_at=old_time)
        )
        db.session.execute(
            update(Review)
            .where(Review.id == newer_review_id)
            .values(created_at=new_time)
        )
        db.session.add_all(
            [
                Vote(review_id=older_review_id, user_id=viewer_id, upvote=True),
                Vote(review_id=older_review_id, user_id=extra_voter_id, upvote=True),
                Vote(review_id=newer_review_id, user_id=viewer_id, upvote=False),
            ]
        )
        db.session.commit()

        with integration_app.test_request_context("/"):
            g.user = SimpleNamespace(id=viewer_id)

            assert review_services.get_review_count(42) == 2
            assert review_services.get_review_count(None, query="heat") == 2

            oldest_reviews = review_services.get_reviews(1, 42, "oldest")
            assert [review.id for review in oldest_reviews] == [
                older_review_id,
                newer_review_id,
            ]

            most_voted_reviews = review_services.get_reviews(1, 42, "most_voted")
            assert [review.id for review in most_voted_reviews] == [
                older_review_id,
                newer_review_id,
            ]
            assert most_voted_reviews[0].vote_data.upvotes == 2
            assert most_voted_reviews[0].vote_data.downvotes == 0
            assert most_voted_reviews[0].vote_data.user_upvote == 1
            assert most_voted_reviews[1].vote_data.upvotes == 0
            assert most_voted_reviews[1].vote_data.downvotes == 1
            assert most_voted_reviews[1].vote_data.user_upvote == 0
