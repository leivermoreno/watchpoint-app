from datetime import datetime, timedelta, timezone

from flask import abort, current_app
import requests
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from ..db import db
from .models import Title, TitleSearchCache

WATCHMODE_TIMEOUT = (3.05, 10)
SEARCH_MIN_LENGTH = 3
SEARCH_MAX_LENGTH = 100
SEARCH_CACHE_TTL = timedelta(hours=24)
TITLE_CACHE_TTL = timedelta(days=7)


def api_key():
    return current_app.config["WATCHPOINT_WATCHMODE_API_KEY"]


def _get_watchmode_json(url, params, abort_on_error=True):
    try:
        response = requests.get(url, params=params, timeout=WATCHMODE_TIMEOUT)
        if response.status_code == requests.codes.ok:
            return response.json()
    except requests.exceptions.RequestException:
        current_app.logger.warning("Watchmode request failed", exc_info=True)
        if abort_on_error:
            abort(503, description="Watchmode is temporarily unavailable.")

    return None


def clean_search_query(value):
    return " ".join(value.split())


def search_query_length_error(query):
    if len(query) < SEARCH_MIN_LENGTH:
        return "too_short", f"Search must be at least {SEARCH_MIN_LENGTH} characters"

    if len(query) > SEARCH_MAX_LENGTH:
        return "too_long", f"Search must be {SEARCH_MAX_LENGTH} characters or fewer"

    return None, None


def normalize_search_query(value):
    return clean_search_query(value).casefold()


def _is_fresh(fetched_at, ttl):
    if fetched_at is None:
        return False

    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)

    return fetched_at >= datetime.now(timezone.utc) - ttl


def get_autocomplete_titles(s):
    query = clean_search_query(s)
    error, _ = search_query_length_error(query)
    if error == "too_short":
        return None

    if error == "too_long":
        abort(400, description="Search query is too long.")

    cache_key = normalize_search_query(query)
    cached = db.session.get(TitleSearchCache, cache_key)
    if cached and _is_fresh(cached.fetched_at, SEARCH_CACHE_TTL):
        return cached.results

    result = _get_watchmode_json(
        "https://api.watchmode.com/v1/autocomplete-search/",
        {"apiKey": api_key(), "search_value": query},
        abort_on_error=cached is None,
    )

    if isinstance(result, dict):
        results = result.get("results")
        if not isinstance(results, list):
            results = []

        upsert_search_cache(cache_key, results)
        return results

    if cached:
        return cached.results

    return None


def upsert_search_cache(query, results):
    stmt = (
        insert(TitleSearchCache)
        .values(query=query, results=results)
        .on_conflict_do_update(
            index_elements=[TitleSearchCache.query],
            set_=dict(results=results, fetched_at=func.now()),
        )
    )
    db.session.execute(stmt)
    db.session.commit()


def get_title_info_or_404(title_id):
    try:
        title_id = int(title_id)
    except ValueError:
        abort(404)

    title = db.session.get(Title, title_id)

    if title and _is_fresh(title.fetched_at, TITLE_CACHE_TTL):
        return title

    fallback_sources = None
    if title and isinstance(title.data, dict):
        fallback_sources = title.data.get("sources")

    result = get_title_data(
        title_id,
        abort_on_error=title is None,
        fallback_sources=fallback_sources,
    )
    if result is None:
        if title:
            return title

        abort(404)

    return upsert_title(result)


def get_title_data(title_id, abort_on_error=True, fallback_sources=None):
    result = _get_watchmode_json(
        f"https://api.watchmode.com/v1/title/{title_id}/details/",
        {"apiKey": api_key()},
        abort_on_error=abort_on_error,
    )

    if not isinstance(result, dict):
        return None

    try:
        result_id = int(result["id"])
    except (KeyError, TypeError, ValueError):
        return None

    if result_id != title_id:
        return None

    result["id"] = result_id
    sources = get_sources(title_id, abort_on_error=abort_on_error)
    if sources is None and fallback_sources is not None:
        sources = fallback_sources

    result["sources"] = sources if sources is not None else []
    return result


def upsert_title(data):
    values = Title.values_from_watchmode(data)
    update_values = {col: values[col] for col in Title.watchmode_column_names()}
    update_values["data"] = values["data"]
    update_values["fetched_at"] = func.now()

    stmt = (
        insert(Title)
        .values(**values)
        .on_conflict_do_update(
            index_elements=[Title.id],
            set_=update_values,
        )
    )
    db.session.execute(stmt)
    db.session.commit()

    title = db.session.get(Title, values["id"])
    if title is None:
        abort(404)

    return title


def get_sources(title_id, abort_on_error=True):
    result = _get_watchmode_json(
        f"https://api.watchmode.com/v1/title/{title_id}/sources/",
        {"apiKey": api_key()},
        abort_on_error=abort_on_error,
    )

    result_filtered = None
    if isinstance(result, list):
        result_filtered = []
        providers = set()
        for src in result:
            if not isinstance(src, dict):
                continue

            provider = src.get("name")
            if src.get("region") == "US" and provider not in providers:
                result_filtered.append(src)

            if provider:
                providers.add(provider)

    return result_filtered
