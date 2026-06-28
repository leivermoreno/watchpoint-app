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

from ..db import db
from .forms import LoginForm, SignupForm
from .models import User
from .utils import next_url_from_request

bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder="templates")


@bp.route("/signup", methods=("GET", "POST"))
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        try:
            user = User(nickname=form.nickname.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Welcome to Watchpoint. You can login now!.", "success")

            return redirect(url_for("auth.login"))

        except IntegrityError:
            db.session.rollback()
            form.nickname.errors.append("Nickname is already taken. Try another one!")

    return render_template("auth_form.html", form=form, page_title="Signup")


@bp.route("/login", methods=("GET", "POST"))
def login():
    form = LoginForm()
    next_url = next_url_from_request()
    if form.validate_on_submit():
        user = db.session.scalar(
            select(User).where(User.nickname == form.nickname.data)
        )
        if user and user.check_password(form.password.data):
            session.clear()
            session.permanent = True
            session["user_id"] = user.id

            return redirect(next_url or url_for("index"))

        form.form_errors.append("Invalid credentials.")

    return render_template(
        "auth_form.html", form=form, page_title="Login", next_url=next_url
    )


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
