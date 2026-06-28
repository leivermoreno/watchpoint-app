from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from flask import Blueprint, g
from jinja2 import ChoiceLoader, FileSystemLoader

from watchpoint.review import blueprint as review_blueprint
from watchpoint.review.models import Review
from watchpoint.title.services import SEARCH_MAX_LENGTH, SEARCH_MIN_LENGTH
from watchpoint.watchlist import blueprint as watchlist_blueprint
from watchpoint.watchlist.models import WATCHLIST_CHOICES

PROJECT_TEMPLATES = Path(__file__).resolve().parents[1] / "watchpoint" / "templates"


@pytest.fixture
def route_app(app):
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TEST_USER"] = SimpleNamespace(id=7)
    app.jinja_loader = ChoiceLoader(
        [app.jinja_loader, FileSystemLoader(PROJECT_TEMPLATES)]
    )

    app.add_url_rule("/", "index", lambda: "index")

    auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

    @auth_bp.get("/login")
    def login():
        return "login"

    @auth_bp.get("/signup")
    def signup():
        return "signup"

    @auth_bp.get("/logout")
    def logout():
        return "logout"

    title_bp = Blueprint("title", __name__)

    @title_bp.get("/<int:title_id>")
    def title_info(title_id):
        return f"title {title_id}"

    @app.before_request
    def load_test_user():
        g.user = app.config["TEST_USER"]

    app.register_blueprint(auth_bp)
    app.register_blueprint(title_bp)
    app.register_blueprint(watchlist_blueprint.bp)
    app.register_blueprint(review_blueprint.bp)

    return app


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


def flashed_messages(client):
    with client.session_transaction() as session:
        return session.get("_flashes", [])


@pytest.mark.parametrize(
    ("method", "path", "kwargs", "expected_next"),
    [
        ("get", "/watchlist/?status=pending", {}, "/watchlist/?status=pending"),
        ("post", "/watchlist/42", {"data": {"watchlist": "pending"}}, None),
        (
            "post",
            "/review/42",
            {"data": {"comment": "This review is long enough.", "stars": "4"}},
            None,
        ),
        ("post", "/review/vote/5", {"data": {"vote": "up"}}, None),
    ],
)
def test_protected_routes_redirect_unauthenticated(
    route_app, monkeypatch, method, path, kwargs, expected_next
):
    route_app.config["TEST_USER"] = None

    monkeypatch.setattr(
        watchlist_blueprint,
        "get_watchlist_by_user",
        lambda *args, **kwargs: pytest.fail("unexpected watchlist lookup"),
    )
    monkeypatch.setattr(
        watchlist_blueprint,
        "get_title_info_or_404",
        lambda *args, **kwargs: pytest.fail("unexpected watchlist title lookup"),
    )
    monkeypatch.setattr(
        review_blueprint,
        "get_title_info_or_404",
        lambda *args, **kwargs: pytest.fail("unexpected review title lookup"),
    )
    monkeypatch.setattr(
        review_blueprint,
        "db",
        SimpleNamespace(
            get_or_404=lambda *args, **kwargs: pytest.fail("unexpected review lookup")
        ),
    )

    client = route_app.test_client()
    response = getattr(client, method)(path, **kwargs)

    location = urlsplit(response.headers["Location"])
    assert response.status_code == 302
    assert location.path == "/auth/login"
    if expected_next:
        assert parse_qs(location.query) == {"next": [expected_next]}
    else:
        assert parse_qs(location.query) == {}
    assert flashed_messages(client) == [("warning", "Log in to continue.")]


def test_get_watchlist_normalizes_invalid_status_to_all(route_app, monkeypatch):
    service_calls = []
    rendered_contexts = []

    def fake_get_watchlist_by_user(status=None):
        service_calls.append(status)
        return FakeScalarResult(["row"])

    def fake_render_template(template, **context):
        rendered_contexts.append((template, context))
        return "watchlist-page"

    monkeypatch.setattr(
        watchlist_blueprint,
        "get_watchlist_by_user",
        fake_get_watchlist_by_user,
    )
    monkeypatch.setattr(watchlist_blueprint, "render_template", fake_render_template)

    response = route_app.test_client().get("/watchlist/?status=bogus")

    assert response.status_code == 200
    assert response.text == "watchlist-page"
    assert service_calls == [None]
    assert rendered_contexts[0][0] == "watchlist.html"
    assert rendered_contexts[0][1]["watchlist"] == ["row"]
    assert rendered_contexts[0][1]["list_choices"] == WATCHLIST_CHOICES
    assert rendered_contexts[0][1]["selected_status"] == "all"


def test_get_watchlist_renders_real_template_contract(route_app, monkeypatch):
    monkeypatch.setattr(
        watchlist_blueprint,
        "get_watchlist_by_user",
        lambda status=None: FakeScalarResult([]),
    )

    response = route_app.test_client().get("/watchlist/")

    assert response.status_code == 200
    assert "Watchlist" in response.text
    assert "Find titles" in response.text


def test_modify_watchlist_upserts_valid_status(route_app, monkeypatch):
    title_calls = []
    upsert_calls = []

    monkeypatch.setattr(
        watchlist_blueprint,
        "get_title_info_or_404",
        lambda title_id: title_calls.append(title_id),
    )
    monkeypatch.setattr(
        watchlist_blueprint,
        "upsert_watchlist",
        lambda title_id, status: upsert_calls.append((title_id, status)),
    )
    monkeypatch.setattr(
        watchlist_blueprint,
        "remove_watchlist",
        lambda title_id: pytest.fail(f"unexpected remove for {title_id}"),
    )

    response = route_app.test_client().post(
        "/watchlist/42",
        data={"watchlist": "pending"},
    )

    assert response.status_code == 302
    assert urlsplit(response.headers["Location"]).path == "/42"
    assert title_calls == [42]
    assert upsert_calls == [(42, "pending")]


def test_modify_watchlist_removes_empty_status(route_app, monkeypatch):
    remove_calls = []

    monkeypatch.setattr(watchlist_blueprint, "get_title_info_or_404", lambda _: None)
    monkeypatch.setattr(
        watchlist_blueprint,
        "upsert_watchlist",
        lambda title_id, status: pytest.fail(
            f"unexpected upsert for {title_id} {status}"
        ),
    )
    monkeypatch.setattr(
        watchlist_blueprint,
        "remove_watchlist",
        lambda title_id: remove_calls.append(title_id),
    )

    response = route_app.test_client().post(
        "/watchlist/42",
        data={"watchlist": ""},
    )

    assert response.status_code == 302
    assert remove_calls == [42]


def test_modify_watchlist_flashes_warning_for_invalid_status(route_app, monkeypatch):
    monkeypatch.setattr(watchlist_blueprint, "get_title_info_or_404", lambda _: None)
    monkeypatch.setattr(
        watchlist_blueprint,
        "upsert_watchlist",
        lambda title_id, status: pytest.fail(
            f"unexpected upsert for {title_id} {status}"
        ),
    )
    monkeypatch.setattr(
        watchlist_blueprint,
        "remove_watchlist",
        lambda title_id: pytest.fail(f"unexpected remove for {title_id}"),
    )

    client = route_app.test_client()
    response = client.post("/watchlist/42", data={"watchlist": "bogus"})

    assert response.status_code == 302
    assert flashed_messages(client) == [("warning", "Choose a valid watchlist status.")]


def test_create_review_valid_form_calls_upsert(route_app, monkeypatch):
    title_calls = []
    upsert_calls = []

    monkeypatch.setattr(
        review_blueprint,
        "get_title_info_or_404",
        lambda title_id: title_calls.append(title_id),
    )
    monkeypatch.setattr(
        review_blueprint,
        "upsert_review",
        lambda title_id, comment, stars: upsert_calls.append(
            (title_id, comment, stars)
        ),
    )

    response = route_app.test_client().post(
        "/review/42",
        data={"comment": "This review is long enough.", "stars": "4"},
    )

    assert response.status_code == 302
    assert urlsplit(response.headers["Location"]).path == "/42"
    assert title_calls == [42]
    assert upsert_calls == [(42, "This review is long enough.", 4)]


def test_create_review_invalid_form_rerenders_title_page(route_app, monkeypatch):
    title_calls = []
    rendered_forms = []

    def fake_render_title_info(title_id, review_form=None):
        rendered_forms.append((title_id, review_form))
        return "title-page"

    monkeypatch.setattr(
        review_blueprint,
        "get_title_info_or_404",
        lambda title_id: title_calls.append(title_id),
    )
    monkeypatch.setattr(
        review_blueprint,
        "upsert_review",
        lambda *args: pytest.fail(f"unexpected review upsert {args}"),
    )
    monkeypatch.setattr(review_blueprint, "render_title_info", fake_render_title_info)

    response = route_app.test_client().post(
        "/review/42",
        data={"comment": "short", "stars": "4"},
    )

    assert response.status_code == 200
    assert response.text == "title-page"
    assert title_calls == [42]
    assert rendered_forms[0][0] == 42
    assert rendered_forms[0][1].errors["comment"]


def test_vote_review_rejects_bad_vote_values(route_app, monkeypatch):
    monkeypatch.setattr(
        review_blueprint,
        "db",
        SimpleNamespace(
            get_or_404=lambda *args: pytest.fail(f"unexpected db lookup {args}")
        ),
    )
    monkeypatch.setattr(
        review_blueprint,
        "toggle_vote",
        lambda *args: pytest.fail(f"unexpected vote toggle {args}"),
    )

    response = route_app.test_client().post(
        "/review/vote/5",
        data={"vote": "sideways"},
    )

    assert response.status_code == 400


def test_vote_review_calls_toggle_vote(route_app, monkeypatch):
    db_calls = []
    toggle_calls = []

    monkeypatch.setattr(
        review_blueprint,
        "db",
        SimpleNamespace(
            get_or_404=lambda model, key: db_calls.append((model, key)) or object()
        ),
    )
    monkeypatch.setattr(
        review_blueprint,
        "toggle_vote",
        lambda review_id, upvote: toggle_calls.append((review_id, upvote)),
    )

    response = route_app.test_client().post("/review/vote/5", data={"vote": "up"})

    assert response.status_code == 302
    assert urlsplit(response.headers["Location"]).path == "/review/"
    assert db_calls == [(Review, 5)]
    assert toggle_calls == [(5, True)]


def test_vote_review_respects_safe_next(route_app, monkeypatch):
    monkeypatch.setattr(
        review_blueprint,
        "db",
        SimpleNamespace(get_or_404=lambda model, key: object()),
    )
    monkeypatch.setattr(review_blueprint, "toggle_vote", lambda *_: None)

    response = route_app.test_client().post(
        "/review/vote/5",
        data={"vote": "down", "next": "/watchlist/?status=pending"},
    )

    location = urlsplit(response.headers["Location"])
    assert response.status_code == 302
    assert location.path == "/watchlist/"
    assert parse_qs(location.query) == {"status": ["pending"]}


def test_show_reviews_normalizes_invalid_page_and_sort(route_app, monkeypatch):
    count_calls = []
    reviews_calls = []
    rendered_contexts = []

    def fake_get_review_count(title_id, query=None, exclude_user_id=None):
        count_calls.append((title_id, query, exclude_user_id))
        return 12

    def fake_get_reviews(page, title_id, sort_by, query=None):
        reviews_calls.append((page, title_id, sort_by, query))
        return ["review"]

    def fake_render_template(template, **context):
        rendered_contexts.append((template, context))
        return "reviews-page"

    monkeypatch.setattr(review_blueprint, "get_review_count", fake_get_review_count)
    monkeypatch.setattr(review_blueprint, "get_reviews", fake_get_reviews)
    monkeypatch.setattr(review_blueprint, "render_template", fake_render_template)

    response = route_app.test_client().get("/review/?page=not-a-number&sort_by=bad")

    assert response.status_code == 200
    assert response.text == "reviews-page"
    assert count_calls == [(None, None, None)]
    assert reviews_calls == [(1, None, "newest", None)]
    assert rendered_contexts[0][0] == "show_reviews.html"
    assert rendered_contexts[0][1]["reviews"] == ["review"]
    assert rendered_contexts[0][1]["page"] == 1
    assert rendered_contexts[0][1]["pages"] == 2
    assert rendered_contexts[0][1]["has_reviews"] is True
    assert rendered_contexts[0][1]["title"] is None
    assert rendered_contexts[0][1]["title_id"] is None
    assert rendered_contexts[0][1]["review_filter_args"] == {}
    assert rendered_contexts[0][1]["sort_by"] == "newest"
    assert (
        rendered_contexts[0][1]["sort_options"] == review_blueprint.REVIEW_SORT_OPTIONS
    )
    assert rendered_contexts[0][1]["search_min_length"] == SEARCH_MIN_LENGTH
    assert rendered_contexts[0][1]["search_max_length"] == SEARCH_MAX_LENGTH
    assert rendered_contexts[0][1]["review_title_query"] == ""


def test_show_reviews_renders_real_template_contract(route_app, monkeypatch):
    monkeypatch.setattr(review_blueprint, "get_review_count", lambda *_, **__: 0)
    monkeypatch.setattr(review_blueprint, "get_reviews", lambda *_, **__: [])

    response = route_app.test_client().get("/review/?q=Heat")

    assert response.status_code == 200
    assert "Reviews" in response.text
    assert 'No reviews found for "Heat".' in response.text


def test_show_reviews_handles_too_long_queries(route_app, monkeypatch):
    monkeypatch.setattr(
        review_blueprint,
        "get_review_count",
        lambda *args, **kwargs: pytest.fail("unexpected count query"),
    )
    monkeypatch.setattr(
        review_blueprint,
        "get_reviews",
        lambda *args, **kwargs: pytest.fail("unexpected reviews query"),
    )

    response = route_app.test_client().get(
        f"/review/?q={'x' * (SEARCH_MAX_LENGTH + 1)}"
    )

    assert response.status_code == 400


def test_autocomplete_review_titles_hides_too_short_query(route_app, monkeypatch):
    rendered_contexts = []

    def fake_render_template(template, **context):
        rendered_contexts.append((template, context))
        return "review-title-results"

    monkeypatch.setattr(
        review_blueprint,
        "get_reviewed_title_matches",
        lambda query: pytest.fail(f"unexpected reviewed title search {query!r}"),
    )
    monkeypatch.setattr(review_blueprint, "render_template", fake_render_template)

    response = route_app.test_client().get(
        f"/review/autocomplete?q={'x' * (SEARCH_MIN_LENGTH - 1)}"
    )

    assert response.status_code == 200
    assert response.text == "review-title-results"
    assert rendered_contexts == [
        (
            "_autocomplete_results.html",
            {
                "results_overlay": True,
                "results_id": "reviewTitleSearchResults",
                "results_endpoint": "review.show_reviews",
                "titles": [],
                "show_results": False,
                "empty_message": "No reviewed titles",
            },
        )
    ]


def test_autocomplete_review_titles_shows_too_long_message(route_app, monkeypatch):
    rendered_contexts = []

    def fake_render_template(template, **context):
        rendered_contexts.append((template, context))
        return "review-title-results"

    monkeypatch.setattr(
        review_blueprint,
        "get_reviewed_title_matches",
        lambda query: pytest.fail(f"unexpected reviewed title search {query!r}"),
    )
    monkeypatch.setattr(review_blueprint, "render_template", fake_render_template)

    response = route_app.test_client().get(
        f"/review/autocomplete?q={'x' * (SEARCH_MAX_LENGTH + 1)}"
    )

    assert response.status_code == 200
    assert response.text == "review-title-results"
    assert rendered_contexts == [
        (
            "_autocomplete_results.html",
            {
                "results_overlay": True,
                "results_id": "reviewTitleSearchResults",
                "results_endpoint": "review.show_reviews",
                "titles": [],
                "message": f"Search must be {SEARCH_MAX_LENGTH} characters or fewer",
                "show_results": True,
                "empty_message": "No reviewed titles",
            },
        )
    ]


def test_autocomplete_review_titles_returns_matches(route_app, monkeypatch):
    search_calls = []
    rendered_contexts = []
    titles = [SimpleNamespace(id=42, name="Heat")]

    def fake_render_template(template, **context):
        rendered_contexts.append((template, context))
        return "review-title-results"

    monkeypatch.setattr(
        review_blueprint,
        "get_reviewed_title_matches",
        lambda query: search_calls.append(query) or titles,
    )
    monkeypatch.setattr(review_blueprint, "render_template", fake_render_template)

    response = route_app.test_client().get("/review/autocomplete?q=  Heat  ")

    assert response.status_code == 200
    assert response.text == "review-title-results"
    assert search_calls == ["Heat"]
    assert rendered_contexts == [
        (
            "_autocomplete_results.html",
            {
                "results_overlay": True,
                "results_id": "reviewTitleSearchResults",
                "results_endpoint": "review.show_reviews",
                "titles": titles,
                "show_results": True,
                "empty_message": "No reviewed titles matching that search",
            },
        )
    ]
