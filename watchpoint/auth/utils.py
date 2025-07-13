from flask import g, redirect, url_for
from functools import wraps


def validate_credentials(nickname, password):
    if len(nickname) < 3 or len(password) < 7:
        return "Must provide, nickname >= 3 characters, and password >= 7 characters."


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for("auth.login"))

        if view:
            return view(*args, **kwargs)

    return wrapper
