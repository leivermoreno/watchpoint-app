import math
from flask import Blueprint, abort, redirect, render_template, request, url_for

from ..title.services import get_title_info_or_404
from ..title.blueprint import render_title_info
from .services import (
    upsert_review,
    get_reviews,
    get_review_count,
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

    title_id = request.args.get("title_id", "").strip()
    title = get_title_info_or_404(title_id) if title_id else None

    review_count = get_review_count(title_id)
    has_reviews = review_count > 0
    pages = math.ceil(review_count / REVIEW_PAGE_LIMIT)
    if page > pages:
        page = pages
    page = max(page, 1)

    sort_by = request.args.get("sort_by")
    if sort_by not in REVIEW_SORT_OPTIONS:
        sort_by = "newest"

    reviews = get_reviews(page, title_id, sort_by)

    return render_template(
        "show_reviews.html",
        reviews=reviews,
        page=page,
        pages=pages,
        has_reviews=has_reviews,
        title=title,
        title_id=title_id,
        sort_by=sort_by,
        sort_options=REVIEW_SORT_OPTIONS,
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
