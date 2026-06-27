from pathlib import Path

import pytest
from flask import Blueprint, g
from jinja2 import ChoiceLoader, FileSystemLoader
from werkzeug.exceptions import ServiceUnavailable

from watchpoint.title import blueprint as title_blueprint
from watchpoint.title.services import SEARCH_MAX_LENGTH, SEARCH_MIN_LENGTH

PROJECT_TEMPLATES = Path(__file__).resolve().parents[1] / "watchpoint" / "templates"


@pytest.fixture
def title_app(app):
    app.config["TEST_USER"] = None
    app.jinja_loader = ChoiceLoader(
        [app.jinja_loader, FileSystemLoader(PROJECT_TEMPLATES)]
    )

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

    review_bp = Blueprint("review", __name__, url_prefix="/review")

    @review_bp.get("/")
    def show_reviews():
        return "reviews"

    @app.before_request
    def load_test_user():
        g.user = app.config["TEST_USER"]

    app.register_blueprint(title_blueprint.bp)
    app.add_url_rule("/", "index", title_blueprint.index)
    app.register_blueprint(auth_bp)
    app.register_blueprint(review_bp)
    return app


def test_search_results_context_hides_unsubmitted_short_query():
    context = title_blueprint.search_results_context(
        "x" * (SEARCH_MIN_LENGTH - 1),
        query_submitted=False,
    )

    assert context == {
        "titles": [],
        "message": None,
        "show_results": False,
    }


def test_search_results_context_shows_submitted_short_query_message():
    context = title_blueprint.search_results_context(
        "x" * (SEARCH_MIN_LENGTH - 1),
        query_submitted=True,
    )

    assert context == {
        "titles": [],
        "message": f"Search must be at least {SEARCH_MIN_LENGTH} characters",
        "show_results": True,
    }


def test_search_results_context_shows_too_long_query_message(monkeypatch):
    def fail_if_called(query):
        raise AssertionError(f"unexpected autocomplete call for {query!r}")

    monkeypatch.setattr(title_blueprint, "get_autocomplete_titles", fail_if_called)

    context = title_blueprint.search_results_context("x" * (SEARCH_MAX_LENGTH + 1))

    assert context == {
        "titles": [],
        "message": f"Search must be {SEARCH_MAX_LENGTH} characters or fewer",
        "show_results": True,
    }


def test_search_results_context_returns_valid_autocomplete_titles(monkeypatch):
    calls = []

    def fake_get_autocomplete_titles(query):
        calls.append(query)
        return [
            {"id": "42", "name": "Heat"},
            {"id": "not-an-int", "name": "Bad ID"},
            {"id": 99, "name": "Alien"},
        ]

    monkeypatch.setattr(
        title_blueprint,
        "get_autocomplete_titles",
        fake_get_autocomplete_titles,
    )

    context = title_blueprint.search_results_context("heat")

    assert calls == ["heat"]
    assert context == {
        "titles": [
            {"id": 42, "name": "Heat"},
            {"id": 99, "name": "Alien"},
        ],
        "message": None,
        "show_results": True,
    }


def test_search_results_context_shows_watchmode_503_fallback(monkeypatch):
    def fake_get_autocomplete_titles(query):
        raise ServiceUnavailable()

    monkeypatch.setattr(
        title_blueprint,
        "get_autocomplete_titles",
        fake_get_autocomplete_titles,
    )

    context = title_blueprint.search_results_context("heat")

    assert context == {
        "titles": [],
        "message": "Search is temporarily unavailable",
        "show_results": True,
    }


def test_index_htmx_request_renders_autocomplete_fragment(title_app, monkeypatch):
    autocomplete_calls = []
    rendered_contexts = []

    def fake_get_autocomplete_titles(query):
        autocomplete_calls.append(query)
        return [{"id": "42", "name": "Heat"}]

    def fake_render_autocomplete_results(**context):
        rendered_contexts.append(context)
        return "autocomplete-fragment"

    monkeypatch.setattr(
        title_blueprint,
        "get_autocomplete_titles",
        fake_get_autocomplete_titles,
    )
    monkeypatch.setattr(
        title_blueprint,
        "render_autocomplete_results",
        fake_render_autocomplete_results,
    )

    response = title_app.test_client().get(
        "/?q=  Heat  ",
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert response.text == "autocomplete-fragment"
    assert "HX-Replace-Url" not in response.headers
    assert autocomplete_calls == ["Heat"]
    assert rendered_contexts == [
        {
            "titles": [{"id": 42, "name": "Heat"}],
            "message": None,
            "show_results": True,
        }
    ]


def test_index_htmx_empty_query_replaces_url(title_app, monkeypatch):
    rendered_contexts = []

    def fail_if_called(query):
        raise AssertionError(f"unexpected autocomplete call for {query!r}")

    def fake_render_autocomplete_results(**context):
        rendered_contexts.append(context)
        return "empty-fragment"

    monkeypatch.setattr(title_blueprint, "get_autocomplete_titles", fail_if_called)
    monkeypatch.setattr(
        title_blueprint,
        "render_autocomplete_results",
        fake_render_autocomplete_results,
    )

    response = title_app.test_client().get(
        "/?q=",
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert response.text == "empty-fragment"
    assert response.headers["HX-Replace-Url"] == "/"
    assert rendered_contexts == [
        {
            "titles": [],
            "message": None,
            "show_results": False,
        }
    ]


def test_index_full_page_renders_template_contract(title_app, monkeypatch):
    autocomplete_calls = []

    def fake_get_autocomplete_titles(query):
        autocomplete_calls.append(query)
        return [{"id": "42", "name": "Heat"}]

    monkeypatch.setattr(
        title_blueprint,
        "get_autocomplete_titles",
        fake_get_autocomplete_titles,
    )

    response = title_app.test_client().get("/?q=  Heat  ")

    assert response.status_code == 200
    assert autocomplete_calls == ["Heat"]
    assert 'value="Heat"' in response.text
    assert f'minlength="{SEARCH_MIN_LENGTH}"' in response.text
    assert f'maxlength="{SEARCH_MAX_LENGTH}"' in response.text
    assert 'href="/42"' in response.text
    assert 'href="/"' in response.text
    assert 'href="/review/"' in response.text
    assert 'href="/auth/login"' in response.text
    assert 'href="/auth/signup"' in response.text
