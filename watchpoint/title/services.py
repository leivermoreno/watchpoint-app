from flask import abort, current_app
import requests
from db import db
from title.models import Title

api_key = lambda: current_app.config["WATCHMODE_API_KEY"]


def get_autocomplete_titles(s):
    r = requests.get(
        "https://api.watchmode.com/v1/autocomplete-search/",
        params={"apiKey": api_key(), "search_value": s},
    )

    results = None
    if r.status_code == requests.codes.ok:
        results = r.json()["results"]

    return results


def get_title_info(title_id):
    title = db.session.get(Title, title_id)

    if not title:
        r = requests.get(
            f"https://api.watchmode.com/v1/title/{title_id}/details/",
            params={"apiKey": api_key()},
        )

        if not r.status_code == requests.codes.ok:
            abort(404, "Title not found")

        result = r.json()
        result["sources"] = get_sources(title_id)
        title = Title(id=result["id"], data=result)
        db.session.add(title)
        db.session.commit()

    return title


def get_sources(title_id):
    r = requests.get(
        f"https://api.watchmode.com/v1/title/{title_id}/sources/",
        params={"apiKey": api_key()},
    )

    result = None
    if not r.status_code == requests.codes.ok:
        abort(404, "Sources not found")

    result = r.json()
    result_filtered = []
    providers = set()
    for src in result:
        if src["region"] == "US" and src["name"] not in providers:
            result_filtered.append(src)
        providers.add(src["name"])

    return result_filtered
