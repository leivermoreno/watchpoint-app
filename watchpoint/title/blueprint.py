from flask import Blueprint, flash, g, render_template, request

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
    title = ""
    titles = None
    if request.args.get("title"):
        title = clean_search_query(request.args["title"])
        if len(title) < SEARCH_MIN_LENGTH:
            flash(f"Write at least {SEARCH_MIN_LENGTH} characters")
        elif len(title) > SEARCH_MAX_LENGTH:
            title = title[:SEARCH_MAX_LENGTH]
            flash(f"Search must be {SEARCH_MAX_LENGTH} characters or fewer")
        else:
            titles = get_autocomplete_titles(title)

    return render_template(
        "search.html",
        title=title,
        titles=titles,
        search_min_length=SEARCH_MIN_LENGTH,
        search_max_length=SEARCH_MAX_LENGTH,
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
