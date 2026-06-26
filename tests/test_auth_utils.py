from urllib.parse import parse_qs, urlsplit

from flask import Blueprint, g

from watchpoint.auth.utils import (
    current_url_for_next,
    login_required,
    next_url_from_request,
    normalize_next_url,
)

TEST_BASE_URL = "https://watchpoint.test"
WATCHLIST_PENDING_URL = "/watchlist/?status=pending"
WATCHLIST_COMPLETED_URL = "/watchlist/?status=completed"
TITLE_URL = "/title/42"
TITLE_REVIEWS_URL = "/title/42?tab=reviews"
TITLE_EDIT_REVIEW_URL = "/title/42?edit_review=1"
REVIEW_URL = "/reviews/42"


def test_normalize_next_url_accepts_safe_local_urls(app):
    with app.test_request_context("/", base_url=TEST_BASE_URL):
        assert normalize_next_url(WATCHLIST_PENDING_URL) == WATCHLIST_PENDING_URL
        assert (
            normalize_next_url(f"{TEST_BASE_URL}{TITLE_REVIEWS_URL}")
            == TITLE_REVIEWS_URL
        )


def test_normalize_next_url_rejects_unsafe_or_invalid_urls(app):
    with app.test_request_context("/", base_url=TEST_BASE_URL):
        for target in (
            "",
            None,
            "https://example.test/watchlist/",
            "//example.test/watchlist/",
            "watchlist/",
        ):
            assert normalize_next_url(target) is None, target


def test_next_url_from_request_returns_none_for_empty_next(app):
    with app.test_request_context("/auth/login?next=", base_url=TEST_BASE_URL):
        assert next_url_from_request() is None


def test_current_url_for_next_uses_get_path_and_query(app):
    with app.test_request_context(WATCHLIST_COMPLETED_URL, method="GET"):
        assert current_url_for_next() == WATCHLIST_COMPLETED_URL


def test_current_url_for_next_uses_post_next_form_value(app):
    with app.test_request_context(
        REVIEW_URL,
        method="POST",
        data={"next": TITLE_EDIT_REVIEW_URL},
    ):
        assert current_url_for_next() == TITLE_EDIT_REVIEW_URL


def test_current_url_for_next_falls_back_to_safe_referrer(app):
    with app.test_request_context(
        REVIEW_URL,
        method="POST",
        base_url=TEST_BASE_URL,
        headers={"Referer": f"{TEST_BASE_URL}{TITLE_URL}"},
    ):
        assert current_url_for_next() == TITLE_URL


def test_current_url_for_next_ignores_bad_post_next_before_safe_referrer(app):
    with app.test_request_context(
        REVIEW_URL,
        method="POST",
        base_url=TEST_BASE_URL,
        data={"next": "https://example.test/title/42"},
        headers={"Referer": f"{TEST_BASE_URL}{TITLE_URL}"},
    ):
        assert current_url_for_next() == TITLE_URL


def test_current_url_for_next_rejects_external_referrer(app):
    with app.test_request_context(
        REVIEW_URL,
        method="POST",
        base_url=TEST_BASE_URL,
        headers={"Referer": "https://example.test/title/42"},
    ):
        assert current_url_for_next() is None


def register_login_required_test_routes(app):
    auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

    @auth_bp.get("/login")
    def login():
        return "login"

    app.register_blueprint(auth_bp)

    @app.before_request
    def load_test_user():
        g.user = app.config.get("TEST_USER")

    @app.get("/private")
    @login_required
    def private():
        app.config["PRIVATE_VIEW_CALLED"] = True
        return "private"


def test_login_required_redirects_unauthenticated_users_to_login(app):
    register_login_required_test_routes(app)

    response = app.test_client().get("/private?tab=reviews")

    assert response.status_code == 302
    location = response.headers["Location"]
    assert urlsplit(location).path == "/auth/login"
    assert parse_qs(urlsplit(location).query) == {"next": ["/private?tab=reviews"]}
    assert app.config.get("PRIVATE_VIEW_CALLED") is None


def test_login_required_calls_wrapped_view_for_authenticated_users(app):
    app.config["TEST_USER"] = object()
    register_login_required_test_routes(app)

    response = app.test_client().get("/private")

    assert response.status_code == 200
    assert response.text == "private"
    assert app.config["PRIVATE_VIEW_CALLED"] is True
