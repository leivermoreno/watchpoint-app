from flask import Blueprint, render_template


bp = Blueprint("title", __name__, template_folder="templates")


@bp.route("/")
def index():
    return render_template("search.html")
