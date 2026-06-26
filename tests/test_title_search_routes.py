import pytest
from werkzeug.exceptions import ServiceUnavailable

from watchpoint.title import blueprint as title_blueprint
from watchpoint.title.services import SEARCH_MAX_LENGTH, SEARCH_MIN_LENGTH


@pytest.fixture
def title_app(app):
    app.register_blueprint(title_blueprint.bp)
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
