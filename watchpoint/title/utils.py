from flask import current_app
import requests

api_key = lambda: current_app.config["WATCHMODE_API_KEY"]


def get_autocomplete_titles(s):
    r = requests.get(
        "https://api.watchmode.com/v1/autocomplete-search/",
        params={"apiKey": api_key(), "search_value": s},
    )

    if not r.status_code == requests.codes.ok:
        results = []
    else:
        results = r.json()["results"]

    return results
