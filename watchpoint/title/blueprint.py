from flask import (
    Blueprint,
    abort,
    flash,
    render_template,
    request,
)

from title.services import get_autocomplete_titles, get_title_info

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

    return render_template(
        "title_info.html",
        info=title.data,
        watchlist=title.watchlist and title.watchlist.list,
    )
