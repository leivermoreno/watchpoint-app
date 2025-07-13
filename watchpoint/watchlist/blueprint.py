from flask import Blueprint, abort, request, redirect, url_for, g


from auth.utils import login_required
from title.services import get_title_info
from watchlist.models import Watchlist, WATCHLIST_CHOICES


bp = Blueprint(
    "watchlist", __name__, url_prefix="/watchlist", template_folder="templates"
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
