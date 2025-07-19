from flask import Blueprint, abort, redirect, request, url_for

from title.services import get_title_info
from review.services import upsert_review
from auth.utils import login_required


bp = Blueprint("review", __name__, url_prefix="/review", template_folder="templates")


@bp.route("/<int:title_id>", methods=("POST",))
@login_required
def create_review(title_id):
    title = get_title_info(title_id)
    if not title:
        abort(404)

    comment = request.form["comment"]
    try:
        stars = int(request.form["stars"])
    except ValueError:
        abort(400)

    if len(comment.strip()) < 10 or stars < 1 or stars > 5:
        abort(400)

    upsert_review(title_id, comment, stars)

    return redirect(url_for("title.title_info", title_id=title_id))
