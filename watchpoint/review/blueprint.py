import math
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from title.services import get_title_info
from review.services import (
    upsert_review,
    get_reviews,
    get_review_count,
    REVIEW_PAGE_LIMIT,
    REVIEW_SORT_OPTIONS,
    upsert_vote,
)
from review.models import Review
from auth.utils import login_required
from db import db


bp = Blueprint("review", __name__, url_prefix="/review", template_folder="templates")


@bp.route("/")
def show_reviews():
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1

    title_id = request.args.get("title_id", "").strip()
    title = None
    if title_id:
        try:
            title_id = int(title_id)
            title = get_title_info(title_id)
            if not title:
                abort(404)
        except ValueError:
            abort(404)

    review_count = get_review_count(title_id)
    pages = math.ceil(review_count / REVIEW_PAGE_LIMIT)
    if page > pages:
        page = pages

    sort_by = request.args.get("sort_by")
    if sort_by not in REVIEW_SORT_OPTIONS:
        sort_by = "newest"

    reviews = get_reviews(page, title_id, sort_by)

    return render_template(
        "show_reviews.html",
        reviews=reviews,
        page=page,
        pages=pages,
        title=title,
        sort_options=REVIEW_SORT_OPTIONS,
    )


@bp.route("/<int:title_id>", methods=("POST",))
@login_required
def create_review(title_id):
    title = get_title_info(title_id)
    if not title:
        abort(404)

    comment = request.form["comment"]
    try:
        stars = int(request.form["stars"])
        if stars < 1 or stars > 5:
            abort(400)
    except ValueError:
        abort(400)

    if len(comment.strip()) < 10:
        flash("Must provide a comment >10 characters.")
        return redirect(url_for("title.title_info", title_id=title_id, edit_review=1))

    upsert_review(title_id, comment, stars)

    return redirect(url_for("title.title_info", title_id=title_id))


@bp.route("/vote/<int:review_id>")
@login_required
def vote_review(review_id):
    upvote = bool(request.args.get("upvote", "").strip())
    db.get_or_404(Review, review_id)

    upsert_vote(review_id, upvote)
    args = {**request.args}
    if upvote:
        del args["upvote"]

    return redirect(url_for("review.show_reviews", **args))
