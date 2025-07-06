from flask import current_app
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
    result = db.session.get(Title, title_id)

    if result:
        result = result.data
    else:
        r = requests.get(
            f"https://api.watchmode.com/v1/title/{title_id}/details/",
            params={"apiKey": api_key()},
        )

        if r.status_code == requests.codes.ok:
            result = r.json()
            result["sources"] = get_sources(title_id)
            db.session.add(Title(id=result["id"], data=result))
            db.session.commit()

    return result


def get_sources(title_id):
    r = requests.get(
        f"https://api.watchmode.com/v1/title/{title_id}/sources/",
        params={"apiKey": api_key()},
    )

    result = None
    if r.status_code == requests.codes.ok:
        result = r.json()
        result_filtered = []
        providers = set()
        for src in result:
            if src["region"] == "US" and src["name"] not in providers:
                result_filtered.append(src)
            providers.add(src["name"])

    return result_filtered
