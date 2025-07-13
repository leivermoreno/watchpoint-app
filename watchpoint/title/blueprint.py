from flask import Blueprint, flash, redirect, render_template, request, url_for, g

from title.services import get_autocomplete_titles, get_title_info
from title.models import Watchlist
from auth.utils import login_required

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

    return render_template(
        "title_info.html",
        info=title.data,
        watchlist=title.watchlist and title.watchlist.list,
    )


@bp.route("/<int:title_id>/watchlist", methods=("POST",))
@login_required
def modify_watchlist(title_id):
    get_title_info(title_id)

    watchlist = request.form["watchlist"]
    if watchlist in ["pending", "completed", "favorites"]:
        Watchlist.upsert_watchlist(g.user.id, title_id, watchlist)

    return redirect(url_for("title.title_info", title_id=title_id))
