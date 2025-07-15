from flask import Blueprint, abort, render_template, request, redirect, url_for, g


from auth.utils import login_required
from title.services import get_title_info
from watchlist.models import Watchlist, WATCHLIST_CHOICES


bp = Blueprint(
    "watchlist", __name__, url_prefix="/watchlist", template_folder="templates"
)


@bp.route("/")
@login_required
def get_watchlist():
    list = request.args.get("list")
    watchlist = Watchlist.get_by_user(g.user.id, list)

    return render_template(
        "watchlist.html", watchlist=watchlist, list_choices=WATCHLIST_CHOICES
    )


@bp.route("/<int:title_id>", methods=("POST",))
@login_required
def modify_watchlist(title_id):
    title = get_title_info(title_id)
    if not title:
        abort(404)

    watchlist = request.form["watchlist"]
    if watchlist in WATCHLIST_CHOICES:
        Watchlist.upsert_watchlist(g.user.id, title_id, watchlist)

    return redirect(url_for("title.title_info", title_id=title_id))
