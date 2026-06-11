from flask import g, redirect, url_for
from functools import wraps


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for("auth.login"))

        return view(*args, **kwargs)

    return wrapper
