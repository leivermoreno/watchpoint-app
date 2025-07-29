from flask import Blueprint, abort, render_template, request, redirect, url_for


from auth.utils import login_required
from title.services import get_title_info_or_404
from watchlist.models import WATCHLIST_CHOICES
from watchlist.services import get_watchlist_by_user, upsert_watchlist


bp = Blueprint(
    "watchlist", __name__, url_prefix="/watchlist", template_folder="templates"
)


@bp.route("/")
@login_required
def get_watchlist():
    list = request.args.get("list")
    watchlist = get_watchlist_by_user(list).all()

    return render_template(
        "watchlist.html", watchlist=watchlist, list_choices=WATCHLIST_CHOICES
    )


@bp.route("/<int:title_id>", methods=("POST",))
@login_required
def modify_watchlist(title_id):
    get_title_info_or_404(title_id)

    watchlist = request.form["watchlist"]
    if watchlist in WATCHLIST_CHOICES:
        upsert_watchlist(title_id, watchlist)

    return redirect(url_for("title.title_info", title_id=title_id))
