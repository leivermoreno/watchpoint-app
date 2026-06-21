from functools import wraps
from urllib.parse import urlsplit

from flask import flash, g, redirect, request, url_for


def normalize_next_url(target):
    if not target:
        return None

    parsed_target = urlsplit(target)
    if parsed_target.scheme or parsed_target.netloc:
        parsed_host = urlsplit(request.host_url)
        if (
            parsed_target.scheme != parsed_host.scheme
            or parsed_target.netloc != parsed_host.netloc
        ):
            return None

        target = parsed_target.path or "/"
        if parsed_target.query:
            target = f"{target}?{parsed_target.query}"

    if not target.startswith("/") or target.startswith("//"):
        return None

    return target


def next_url_from_request():
    return normalize_next_url(request.form.get("next") or request.args.get("next"))


def current_url_for_next():
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return request.full_path if request.query_string else request.path

    return next_url_from_request() or normalize_next_url(request.referrer)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not g.user:
            next_url = current_url_for_next()
            login_url = (
                url_for("auth.login", next=next_url)
                if next_url
                else url_for("auth.login")
            )
            flash("Log in to continue.", "warning")
            return redirect(login_url)

        return view(*args, **kwargs)

    return wrapper
