import math
from flask import Blueprint, abort, redirect, render_template, request, url_for

from ..title.models import Title
from ..title.services import (
    SEARCH_MAX_LENGTH,
    SEARCH_MIN_LENGTH,
    clean_search_query,
    get_title_info_or_404,
    search_query_length_error,
)
from ..title.blueprint import render_title_info
from .services import (
    upsert_review,
    get_reviews,
    get_review_count,
    get_reviewed_title_matches,
    REVIEW_PAGE_LIMIT,
    REVIEW_SORT_OPTIONS,
    toggle_vote,
)
from .forms import ReviewForm
from .models import Review
from ..auth.utils import login_required
from ..db import db


bp = Blueprint("review", __name__, url_prefix="/review", template_folder="templates")


@bp.route("/")
def show_reviews():
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1

    query = clean_search_query(request.args.get("q", ""))
    error, _ = search_query_length_error(query)
    if error == "too_long":
        abort(400)

    title_id = None
    title_id_arg = request.args.get("title_id", "").strip()
    if title_id_arg:
        try:
            title_id = int(title_id_arg)
        except ValueError:
            abort(404)

    title = db.get_or_404(Title, title_id) if title_id else None
    query_filter = query if query and not title_id else None
    review_filter_args = {"title_id": title_id} if title_id else {}
    if query_filter:
        review_filter_args["q"] = query_filter

    review_count = get_review_count(title_id, query_filter)
    has_reviews = review_count > 0
    pages = math.ceil(review_count / REVIEW_PAGE_LIMIT)
    if page > pages:
        page = pages
    page = max(page, 1)

    sort_by = request.args.get("sort_by")
    if sort_by not in REVIEW_SORT_OPTIONS:
        sort_by = "newest"

    reviews = get_reviews(page, title_id, sort_by, query_filter)

    return render_template(
        "show_reviews.html",
        reviews=reviews,
        page=page,
        pages=pages,
        has_reviews=has_reviews,
        title=title,
        title_id=title_id,
        review_filter_args=review_filter_args,
        sort_by=sort_by,
        sort_options=REVIEW_SORT_OPTIONS,
        search_min_length=SEARCH_MIN_LENGTH,
        search_max_length=SEARCH_MAX_LENGTH,
        review_title_query=query,
    )


@bp.route("/autocomplete")
def autocomplete_review_titles():
    query = clean_search_query(request.args.get("q", ""))
    error, message = search_query_length_error(query)

    if error == "too_short":
        return render_review_title_results(
            titles=[],
            show_results=False,
            empty_message="No reviewed titles",
        )

    if error == "too_long":
        return render_review_title_results(
            titles=[],
            message=message,
            show_results=True,
            empty_message="No reviewed titles",
        )

    return render_review_title_results(
        titles=get_reviewed_title_matches(query),
        show_results=True,
        empty_message="No reviewed titles matching that search",
    )


def render_review_title_results(**context):
    return render_template(
        "_autocomplete_results.html",
        results_overlay=True,
        results_id="reviewTitleSearchResults",
        results_endpoint="review.show_reviews",
        **context,
    )


@bp.route("/<int:title_id>", methods=("POST",))
@login_required
def create_review(title_id):
    get_title_info_or_404(title_id)
    form = ReviewForm()
    if form.validate_on_submit():
        upsert_review(title_id, form.comment.data, form.stars.data)
        return redirect(url_for("title.title_info", title_id=title_id))

    # Invalid: redisplay the title page with the form's inline errors.
    return render_title_info(title_id, review_form=form)


@bp.route("/vote/<int:review_id>", methods=("POST",))
@login_required
def vote_review(review_id):
    vote = request.form.get("vote")
    if vote not in ("up", "down"):
        abort(400)

    db.get_or_404(Review, review_id)

    toggle_vote(review_id, vote == "up")

    # page / sort_by / title_id ride along in the action's query string so the
    # redirect lands back on the same filtered page.
    return redirect(url_for("review.show_reviews", **request.args))
