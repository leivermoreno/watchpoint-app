from flask import Blueprint, g, render_template, request
from werkzeug.exceptions import HTTPException

from .services import (
    SEARCH_MAX_LENGTH,
    SEARCH_MIN_LENGTH,
    clean_search_query,
    get_autocomplete_titles,
    get_title_info_or_404,
)
from ..watchlist.services import get_title_list_by_user
from ..watchlist.models import WATCHLIST_CHOICES
from ..review.services import get_title_review_by_user
from ..review.forms import ReviewForm

bp = Blueprint("title", __name__, template_folder="templates")


@bp.route("/")
def index():
    return render_template(
        "search.html",
        search_min_length=SEARCH_MIN_LENGTH,
        search_max_length=SEARCH_MAX_LENGTH,
        titles=[],
        message=None,
        show_results=False,
    )


@bp.get("/titles/autocomplete")
def autocomplete_titles():
    query = clean_search_query(request.args.get("q", ""))
    if len(query) < SEARCH_MIN_LENGTH:
        return render_autocomplete_results()

    if len(query) > SEARCH_MAX_LENGTH:
        return render_autocomplete_results(
            message=f"Search must be {SEARCH_MAX_LENGTH} characters or fewer",
            show_results=True,
        )

    try:
        titles = get_autocomplete_titles(query) or []
    except HTTPException as exc:
        if exc.code == 503:
            return render_autocomplete_results(
                message="Search is temporarily unavailable",
                show_results=True,
            )

        raise

    return render_autocomplete_results(
        titles=autocomplete_result_titles(titles),
        show_results=True,
    )


def autocomplete_result_titles(titles):
    results = []
    for title in titles:
        try:
            title_id = int(title["id"])
        except (KeyError, TypeError, ValueError):
            continue

        name = title.get("name")
        if not name:
            continue

        results.append({"id": title_id, "name": name})

    return results


def render_autocomplete_results(titles=None, message=None, show_results=False):
    return render_template(
        "_autocomplete_results.html",
        titles=titles or [],
        message=message,
        show_results=show_results,
    )


def render_title_info(title_id, review_form=None):
    title = get_title_info_or_404(title_id)

    watchlist = None
    review = None
    if g.user:
        watchlist = get_title_list_by_user(title_id)
        review = get_title_review_by_user(title_id)

    if review_form is None:
        review_form = ReviewForm(obj=review)

    # Show the editable form for a first-time review, when "Edit review" was
    # clicked, or when a submission failed validation (errors to surface).
    show_review_form = bool(
        not review or request.args.get("edit_review") or review_form.errors
    )

    return render_template(
        "title_info.html",
        info=title,
        watchlist=watchlist and watchlist.status,
        watchlist_choices=WATCHLIST_CHOICES,
        review=review,
        form=review_form,
        show_review_form=show_review_form,
    )


@bp.route("/<int:title_id>")
def title_info(title_id):
    return render_title_info(title_id)
