from werkzeug.datastructures import MultiDict

from watchpoint.auth.models import User
from watchpoint.review.forms import ReviewForm


def make_review_form(app, data):
    with app.test_request_context("/reviews", method="POST"):
        return ReviewForm(formdata=MultiDict(data), meta={"csrf": False})


def test_user_password_helpers_hash_and_verify_passwords():
    password = "correct horse battery staple"
    user = User(nickname="movie-fan")

    user.set_password(password)

    assert user._password != password
    assert password not in user._password
    assert user.check_password(password)
    assert not user.check_password("wrong password")


def test_review_form_accepts_valid_review_and_coerces_stars_to_int(app):
    form = make_review_form(
        app,
        {
            "comment": "This is a thoughtful review.",
            "stars": "4",
        },
    )

    assert form.validate()
    assert form.stars.data == 4
    assert isinstance(form.stars.data, int)


def test_review_form_requires_stars(app):
    form = make_review_form(
        app,
        {"comment": "This is a thoughtful review."},
    )

    assert not form.validate()
    assert "stars" in form.errors


def test_review_form_rejects_short_comment(app):
    form = make_review_form(
        app,
        {
            "comment": "Too short",
            "stars": "4",
        },
    )

    assert not form.validate()
    assert "comment" in form.errors


def test_review_form_rejects_too_long_comment(app):
    form = make_review_form(
        app,
        {
            "comment": "x" * 2001,
            "stars": "4",
        },
    )

    assert not form.validate()
    assert "comment" in form.errors


def test_review_form_rejects_out_of_range_stars(app):
    form = make_review_form(
        app,
        {
            "comment": "This is a thoughtful review.",
            "stars": "6",
        },
    )

    assert not form.validate()
    assert "stars" in form.errors
