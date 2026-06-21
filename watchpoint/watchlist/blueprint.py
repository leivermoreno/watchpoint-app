from flask import Blueprint, flash, render_template, request, redirect, url_for


from ..auth.utils import login_required
from ..title.services import get_title_info_or_404
from .models import WATCHLIST_CHOICES
from .services import get_watchlist_by_user, remove_watchlist, upsert_watchlist


bp = Blueprint(
    "watchlist", __name__, url_prefix="/watchlist", template_folder="templates"
)


@bp.route("/")
@login_required
def get_watchlist():
    selected_status = request.args.get("status", "all")
    if selected_status not in (*WATCHLIST_CHOICES, "all"):
        selected_status = "all"

    status = None if selected_status == "all" else selected_status
    watchlist = get_watchlist_by_user(status).all()

    return render_template(
        "watchlist.html",
        watchlist=watchlist,
        list_choices=WATCHLIST_CHOICES,
        selected_status=selected_status,
    )


@bp.route("/<int:title_id>", methods=("POST",))
@login_required
def modify_watchlist(title_id):
    get_title_info_or_404(title_id)

    watchlist = request.form.get("watchlist")
    if watchlist == "":
        remove_watchlist(title_id)
        flash("Removed from watchlist.", "success")
    elif watchlist in WATCHLIST_CHOICES:
        upsert_watchlist(title_id, watchlist)
        flash("Watchlist updated.", "success")
    else:
        flash("Choose a valid watchlist status.", "warning")

    return redirect(url_for("title.title_info", title_id=title_id))
