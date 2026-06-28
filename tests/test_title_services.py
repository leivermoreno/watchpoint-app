from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from watchpoint.title import services as title_services
from watchpoint.title.models import Title, TitleSearchCache


class FakeSession:
    def __init__(self, item):
        self.item = item
        self.get_calls = []

    def get(self, model, key):
        self.get_calls.append((model, key))
        return self.item


def test_title_values_from_watchmode_maps_denormalized_columns():
    data = {
        "id": 42,
        "title": "Heat",
        "type": "movie",
        "year": 1995,
        "end_year": None,
        "posterLarge": "https://example.test/poster.jpg",
        "plot_overview": "A crew takes scores in Los Angeles.",
        "user_rating": 8.3,
        "critic_score": 88,
        "trailer": "https://example.test/trailer",
        "sources": [{"name": "Kanopy", "region": "US"}],
    }

    values = Title.values_from_watchmode(data)

    assert values == {
        "id": 42,
        "name": "Heat",
        "type": "movie",
        "year": 1995,
        "end_year": None,
        "poster_large": "https://example.test/poster.jpg",
        "plot_overview": "A crew takes scores in Los Angeles.",
        "user_rating": 8.3,
        "critic_score": 88,
        "trailer": "https://example.test/trailer",
        "data": data,
    }
    assert values["data"] is data


def test_title_values_from_watchmode_uses_none_for_missing_denormalized_values():
    values = Title.values_from_watchmode({"id": 42})

    assert values == {
        "id": 42,
        "name": None,
        "type": None,
        "year": None,
        "end_year": None,
        "poster_large": None,
        "plot_overview": None,
        "user_rating": None,
        "critic_score": None,
        "trailer": None,
        "data": {"id": 42},
    }


def test_is_fresh_accepts_timezone_aware_recent_timestamp():
    fetched_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    assert title_services._is_fresh(fetched_at, timedelta(minutes=10))


def test_is_fresh_rejects_timezone_aware_expired_timestamp():
    fetched_at = datetime.now(timezone.utc) - timedelta(minutes=15)

    assert not title_services._is_fresh(fetched_at, timedelta(minutes=10))


def test_is_fresh_treats_naive_timestamp_as_utc():
    fetched_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(
        tzinfo=None
    )

    assert title_services._is_fresh(fetched_at, timedelta(minutes=10))


def test_is_fresh_rejects_missing_timestamp():
    assert not title_services._is_fresh(None, timedelta(minutes=10))


def test_autocomplete_search_cache_key_normalizes_query():
    assert (
        title_services.autocomplete_search_cache_key("  The   MATRIX  ") == "the matrix"
    )


def test_filter_autocomplete_title_results_accepts_title_with_poster():
    assert title_services.filter_autocomplete_title_results(
        [
            {
                "id": "42",
                "name": "  Heat  ",
                "result_type": "title",
                "image_url": " https://example.test/poster.jpg ",
            }
        ]
    ) == [{"id": 42, "name": "Heat"}]


@pytest.mark.parametrize(
    "row",
    [
        {"id": 42, "name": "Heat", "result_type": "title"},
        {"id": 42, "name": "Heat", "result_type": "title", "image_url": ""},
        {"id": 42, "name": "Heat", "result_type": "title", "image_url": "   "},
    ],
)
def test_filter_autocomplete_title_results_rejects_missing_or_blank_image_url(row):
    assert title_services.filter_autocomplete_title_results([row]) == []


def test_filter_autocomplete_title_results_rejects_invalid_rows_and_dedupes_ids():
    rows = [
        {"id": 1, "name": "Person", "result_type": "person", "image_url": "poster"},
        {"id": True, "name": "Bool", "result_type": "title", "image_url": "poster"},
        {"id": 4.2, "name": "Float", "result_type": "title", "image_url": "poster"},
        {"id": "", "name": "Blank ID", "result_type": "title", "image_url": "poster"},
        {
            "id": "   ",
            "name": "Whitespace ID",
            "result_type": "title",
            "image_url": "poster",
        },
        {
            "id": "not-an-int",
            "name": "Bad ID",
            "result_type": "title",
            "image_url": "poster",
        },
        {"id": 7, "name": "", "result_type": "title", "image_url": "poster"},
        {"id": 8, "name": "   ", "result_type": "title", "image_url": "poster"},
        {"id": 9, "result_type": "title", "image_url": "poster"},
        None,
        "bad-row",
        {"id": "42", "name": "Heat", "result_type": "title", "image_url": "poster"},
        {
            "id": 42,
            "name": "Heat Duplicate",
            "result_type": "title",
            "image_url": "poster",
        },
    ]

    assert title_services.filter_autocomplete_title_results(rows) == [
        {"id": 42, "name": "Heat"}
    ]


def test_get_sources_keeps_us_sources_once_per_provider(monkeypatch):
    sources = [
        {"name": "Netflix", "region": "CA", "web_url": "ignored"},
        {"name": "Netflix", "region": "US", "web_url": "netflix-us"},
        {"name": "Netflix", "region": "US", "web_url": "duplicate"},
        {"name": "Kanopy", "region": "US", "web_url": "kanopy"},
        {"name": "BBC iPlayer", "region": "GB", "web_url": "ignored"},
        {"region": "US", "web_url": "missing-provider"},
        {"name": "", "region": "US", "web_url": "blank-provider"},
        None,
        "bad-row",
    ]

    def fake_get_watchmode_json(url, params, abort_on_error=True):
        assert url == "https://api.watchmode.com/v1/title/42/sources/"
        assert params == {"apiKey": "test-api-key"}
        assert abort_on_error is False
        return sources

    monkeypatch.setattr(title_services, "api_key", lambda: "test-api-key")
    monkeypatch.setattr(title_services, "_get_watchmode_json", fake_get_watchmode_json)

    assert title_services.get_sources(42, abort_on_error=False) == [
        {"name": "Netflix", "region": "US", "web_url": "netflix-us"},
        {"name": "Kanopy", "region": "US", "web_url": "kanopy"},
    ]


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"id": None},
        {"id": "not-an-int"},
        {"id": 99},
    ],
)
def test_get_title_data_rejects_bad_or_mismatched_ids(monkeypatch, payload):
    def fail_if_called(title_id, abort_on_error=True):
        raise AssertionError(f"unexpected sources call for {title_id}")

    monkeypatch.setattr(title_services, "api_key", lambda: "test-api-key")
    monkeypatch.setattr(
        title_services,
        "_get_watchmode_json",
        lambda url, params, abort_on_error=True: payload,
    )
    monkeypatch.setattr(title_services, "get_sources", fail_if_called)

    assert title_services.get_title_data(42, abort_on_error=False) is None


def test_get_title_data_uses_fallback_sources_when_source_refresh_fails(monkeypatch):
    fallback_sources = [{"name": "Kanopy", "region": "US"}]
    get_sources_calls = []

    def fake_get_sources(title_id, abort_on_error=True):
        get_sources_calls.append((title_id, abort_on_error))
        return None

    monkeypatch.setattr(title_services, "api_key", lambda: "test-api-key")
    monkeypatch.setattr(
        title_services,
        "_get_watchmode_json",
        lambda url, params, abort_on_error=True: {"id": "42", "title": "Heat"},
    )
    monkeypatch.setattr(title_services, "get_sources", fake_get_sources)

    result = title_services.get_title_data(
        42,
        abort_on_error=False,
        fallback_sources=fallback_sources,
    )

    assert result == {
        "id": 42,
        "title": "Heat",
        "sources": fallback_sources,
    }
    assert get_sources_calls == [(42, False)]


def test_get_title_info_or_404_returns_fresh_cached_title_without_refresh(monkeypatch):
    title = SimpleNamespace(
        id=42,
        name="Heat",
        data={"id": 42},
        fetched_at=datetime.now(timezone.utc),
    )
    session = FakeSession(title)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("unexpected Watchmode refresh")

    monkeypatch.setattr(title_services, "db", SimpleNamespace(session=session))
    monkeypatch.setattr(title_services, "get_title_data", fail_if_called)

    assert title_services.get_title_info_or_404("42") is title
    assert session.get_calls == [(Title, 42)]


def test_get_title_info_or_404_returns_stale_cache_when_refresh_fails(monkeypatch):
    cached_sources = [{"name": "Kanopy", "region": "US"}]
    title = SimpleNamespace(
        id=42,
        name="Heat",
        data={"id": 42, "sources": cached_sources},
        fetched_at=datetime.now(timezone.utc) - title_services.TITLE_CACHE_TTL,
    )
    session = FakeSession(title)
    refresh_calls = []

    def fake_get_title_data(title_id, abort_on_error=True, fallback_sources=None):
        refresh_calls.append((title_id, abort_on_error, fallback_sources))
        return None

    monkeypatch.setattr(title_services, "db", SimpleNamespace(session=session))
    monkeypatch.setattr(title_services, "get_title_data", fake_get_title_data)

    assert title_services.get_title_info_or_404("42") is title
    assert session.get_calls == [(Title, 42)]
    assert refresh_calls == [(42, False, cached_sources)]


def test_get_autocomplete_titles_fetches_title_results_and_caches_normalized_rows(
    monkeypatch,
):
    session = FakeSession(None)
    autocomplete_calls = []
    upsert_calls = []

    def fake_get_watchmode_json(url, params, abort_on_error=True):
        autocomplete_calls.append((url, params, abort_on_error))
        return {
            "results": [
                {
                    "id": "42",
                    "name": "  Heat  ",
                    "result_type": "title",
                    "image_url": "https://example.test/heat.jpg",
                },
                {
                    "id": 42,
                    "name": "Heat Duplicate",
                    "result_type": "title",
                    "image_url": "https://example.test/heat-2.jpg",
                },
                {
                    "id": "7",
                    "name": "Alien",
                    "result_type": "title",
                    "image_url": "https://example.test/alien.jpg",
                },
                {
                    "id": "8",
                    "name": "A Person",
                    "result_type": "person",
                    "image_url": "https://example.test/person.jpg",
                },
            ]
        }

    def fake_upsert_search_cache(query, results):
        upsert_calls.append((query, results))

    monkeypatch.setattr(title_services, "api_key", lambda: "test-api-key")
    monkeypatch.setattr(title_services, "db", SimpleNamespace(session=session))
    monkeypatch.setattr(title_services, "_get_watchmode_json", fake_get_watchmode_json)
    monkeypatch.setattr(title_services, "upsert_search_cache", fake_upsert_search_cache)

    results = title_services.get_autocomplete_titles("  Heat  ")

    assert results == [{"id": 42, "name": "Heat"}, {"id": 7, "name": "Alien"}]
    assert session.get_calls == [(TitleSearchCache, "heat")]
    assert autocomplete_calls == [
        (
            "https://api.watchmode.com/v1/autocomplete-search/",
            {"apiKey": "test-api-key", "search_value": "Heat", "search_type": 2},
            True,
        )
    ]
    assert all("/title/" not in url for url, _, _ in autocomplete_calls)
    assert upsert_calls == [("heat", results)]


def test_get_autocomplete_titles_returns_fresh_cached_search_without_refresh(
    monkeypatch,
):
    cached = SimpleNamespace(
        query="heat",
        results=[{"id": 42, "name": "Heat"}],
        fetched_at=datetime.now(timezone.utc),
    )
    session = FakeSession(cached)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("unexpected Watchmode autocomplete refresh")

    monkeypatch.setattr(title_services, "db", SimpleNamespace(session=session))
    monkeypatch.setattr(title_services, "_get_watchmode_json", fail_if_called)
    monkeypatch.setattr(title_services, "upsert_search_cache", fail_if_called)

    assert title_services.get_autocomplete_titles("  HEAT  ") == [
        {"id": 42, "name": "Heat"}
    ]
    assert session.get_calls == [(TitleSearchCache, "heat")]


def test_get_autocomplete_titles_returns_stale_cache_when_watchmode_fails(
    monkeypatch,
):
    cached = SimpleNamespace(
        query="heat",
        results=[{"id": 42, "name": "Heat"}],
        fetched_at=datetime.now(timezone.utc) - title_services.SEARCH_CACHE_TTL,
    )
    session = FakeSession(cached)
    autocomplete_calls = []

    def fake_get_watchmode_json(url, params, abort_on_error=True):
        autocomplete_calls.append((url, params, abort_on_error))
        return None

    def fail_if_called(*args, **kwargs):
        raise AssertionError("unexpected cache upsert")

    monkeypatch.setattr(title_services, "api_key", lambda: "test-api-key")
    monkeypatch.setattr(title_services, "db", SimpleNamespace(session=session))
    monkeypatch.setattr(title_services, "_get_watchmode_json", fake_get_watchmode_json)
    monkeypatch.setattr(title_services, "upsert_search_cache", fail_if_called)

    assert title_services.get_autocomplete_titles("  HEAT  ") == [
        {"id": 42, "name": "Heat"}
    ]
    assert session.get_calls == [(TitleSearchCache, "heat")]
    assert autocomplete_calls == [
        (
            "https://api.watchmode.com/v1/autocomplete-search/",
            {"apiKey": "test-api-key", "search_value": "HEAT", "search_type": 2},
            False,
        )
    ]
