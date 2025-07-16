from flask import Blueprint, abort, flash, render_template, request, g

from title.services import get_autocomplete_titles, get_title_info
from watchlist.services import get_title_list_by_user
from watchlist.models import WATCHLIST_CHOICES

bp = Blueprint("title", __name__, template_folder="templates")


@bp.route("/")
def index():
    title = ""
    titles = None
    if request.args.get("title"):
        title = request.args["title"].strip()
        if len(title) >= 3:
            titles = get_autocomplete_titles(title)
        else:
            flash("Write at least 3 characters")

    return render_template("search.html", title=title, titles=titles)


@bp.route("/<int:title_id>")
def title_info(title_id):
    title = get_title_info(title_id)
    if not title:
        abort(404)

    watchlist = None
    if g.user:
        watchlist = get_title_list_by_user(title_id)

    return render_template(
        "title_info.html",
        info=title.data,
        watchlist=watchlist and watchlist.list,
        watchlist_choices=WATCHLIST_CHOICES,
    )
