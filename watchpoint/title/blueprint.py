from flask import Blueprint, flash, render_template, request

from title.utils import get_autocomplete_titles


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
