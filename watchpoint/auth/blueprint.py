from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from auth.models import User
from db import db
from auth.utils import validate_credentials

bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder="templates")


@bp.route("/signup", methods=("GET", "POST"))
def signup():
    if request.method == "POST":
        nickname = request.form["nickname"]
        password = request.form["password"]

        error = validate_credentials(nickname, password)
        if not error:
            try:
                user = User(nickname=nickname, password=password)
                db.session.add(user)
                db.session.commit()
                flash("Welcome to Watchpoint. You can login now!.")

                return redirect(url_for("auth.login"))

            except IntegrityError:
                error = "Nickname is already taken. Try another one!"

        flash(error)

    return render_template("signup.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        nickname = request.form["nickname"]
        password = request.form["password"]

        error = validate_credentials(nickname, password)
        if not error:
            user = db.session.scalar(select(User).where(User.nickname == nickname))
            if user and user.check_password(password):
                session.clear()
                session["user_id"] = user.id

                return redirect(url_for("index"))

            error = "Invalid credentials."

        flash(error)

    return render_template("signup.html")


@bp.before_app_request
def load_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = db.session.get_one(User, user_id)


@bp.before_request
def redirect_active_session():
    if request.endpoint != "auth.logout" and g.user:
        return redirect(url_for("index"))


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
