import math

from flask import Blueprint, g, make_response, render_template, request, url_for
from werkzeug.exceptions import HTTPException

from ..review.forms import ReviewForm
from ..review.services import (
    REVIEW_PAGE_LIMIT,
    REVIEW_SORT_OPTIONS,
    get_review_count,
    get_reviews,
    get_title_review_by_user,
)
from ..watchlist.models import WATCHLIST_CHOICES
from ..watchlist.services import get_title_list_by_user
from .services import (
    SEARCH_MAX_LENGTH,
    SEARCH_MIN_LENGTH,
    clean_search_query,
    get_autocomplete_titles,
    get_title_info_or_404,
    search_query_length_error,
)

bp = Blueprint("title", __name__, template_folder="templates")


@bp.route("/")
def index():
    query_submitted = "q" in request.args
    query = clean_search_query(request.args.get("q", ""))
    htmx_request = is_htmx_request()
    results = search_results_context(
        query,
        query_submitted=query_submitted,
        htmx_request=htmx_request,
    )

    if htmx_request:
        response = make_response(render_autocomplete_results(**results))
        if not query:
            response.headers["HX-Replace-Url"] = url_for("title.index")

        return response

    return render_template(
        "search.html",
        search_min_length=SEARCH_MIN_LENGTH,
        search_max_length=SEARCH_MAX_LENGTH,
        query=query,
        results_overlay=False,
        **results,
    )


def is_htmx_request():
    return request.headers.get("HX-Request") == "true"


def search_results_context(query, query_submitted=False, htmx_request=False):
    error, message = search_query_length_error(query)

    if error == "too_short":
        if query_submitted and not htmx_request:
            return dict(
                titles=[],
                message=message,
                show_results=True,
            )

        return dict(titles=[], message=None, show_results=False)

    if error == "too_long":
        return dict(
            titles=[],
            message=message,
            show_results=True,
        )

    try:
        titles = get_autocomplete_titles(query) or []
    except HTTPException as exc:
        if exc.code == 503:
            return dict(
                titles=[],
                message="Search is temporarily unavailable",
                show_results=True,
            )

        raise

    return dict(
        titles=autocomplete_result_titles(titles),
        message=None,
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


def render_autocomplete_results(
    titles=None, message=None, show_results=False, results_overlay=True
):
    return render_template(
        "_autocomplete_results.html",
        titles=titles or [],
        message=message,
        show_results=show_results,
        results_overlay=results_overlay,
    )


# Shared by the title page route and review validation failures, where the
# submitted form needs to be rendered again with inline errors.
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

    review_sort_by = request.args.get("sort_by")
    if review_sort_by not in REVIEW_SORT_OPTIONS:
        review_sort_by = "newest"

    exclude_user_id = g.user.id if g.user else None
    title_review_count = get_review_count(title_id, exclude_user_id=exclude_user_id)
    title_review_pages = math.ceil(title_review_count / REVIEW_PAGE_LIMIT)
    title_reviews = get_reviews(
        1,
        title_id,
        review_sort_by,
        exclude_user_id=exclude_user_id,
    )

    return render_template(
        "title_info.html",
        info=title,
        watchlist=watchlist and watchlist.status,
        watchlist_choices=WATCHLIST_CHOICES,
        review=review,
        form=review_form,
        show_review_form=show_review_form,
        title_reviews=title_reviews,
        title_review_count=title_review_count,
        title_review_pages=title_review_pages,
        review_sort_by=review_sort_by,
        review_sort_options=REVIEW_SORT_OPTIONS,
    )


@bp.route("/<int:title_id>")
def title_info(title_id):
    return render_title_info(title_id)
