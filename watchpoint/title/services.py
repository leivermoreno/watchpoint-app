from flask import abort, current_app
import requests
from ..db import db
from .models import Title

api_key = lambda: current_app.config["WATCHPOINT_WATCHMODE_API_KEY"]
WATCHMODE_TIMEOUT = (3.05, 10)


def _get_watchmode_json(url, params):
    try:
        response = requests.get(url, params=params, timeout=WATCHMODE_TIMEOUT)
        if response.status_code == requests.codes.ok:
            return response.json()
    except requests.exceptions.RequestException:
        current_app.logger.warning("Watchmode request failed")
        abort(503, description="Watchmode is temporarily unavailable.")

    return None


def get_autocomplete_titles(s):
    result = _get_watchmode_json(
        "https://api.watchmode.com/v1/autocomplete-search/",
        {"apiKey": api_key(), "search_value": s},
    )

    results = None
    if result is not None:
        results = result["results"]

    return results


def get_title_info_or_404(title_id):
    try:
        title_id = int(title_id)
    except ValueError:
        abort(404)

    title = db.session.get(Title, title_id)

    if not title:
        result = _get_watchmode_json(
            f"https://api.watchmode.com/v1/title/{title_id}/details/",
            {"apiKey": api_key()},
        )

        if result is not None:
            result["sources"] = get_sources(title_id) or []
            title = Title.from_watchmode(result)
            db.session.add(title)
            db.session.commit()
        else:
            abort(404)

    return title


def get_sources(title_id):
    result = _get_watchmode_json(
        f"https://api.watchmode.com/v1/title/{title_id}/sources/",
        {"apiKey": api_key()},
    )

    result_filtered = None
    if result is not None:
        result_filtered = []
        providers = set()
        for src in result:
            if src["region"] == "US" and src["name"] not in providers:
                result_filtered.append(src)
            providers.add(src["name"])

    return result_filtered
