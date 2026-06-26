from watchpoint.auth.utils import current_url_for_next, normalize_next_url


def test_normalize_next_url_accepts_safe_relative_url(app):
    with app.test_request_context("/", base_url="https://watchpoint.test"):
        assert normalize_next_url("/watchlist/?status=pending") == (
            "/watchlist/?status=pending"
        )


def test_normalize_next_url_converts_same_origin_absolute_url(app):
    with app.test_request_context("/", base_url="https://watchpoint.test"):
        assert normalize_next_url("https://watchpoint.test/title/42?tab=reviews") == (
            "/title/42?tab=reviews"
        )


def test_normalize_next_url_rejects_external_url(app):
    with app.test_request_context("/", base_url="https://watchpoint.test"):
        assert normalize_next_url("https://example.test/watchlist/") is None


def test_normalize_next_url_rejects_protocol_relative_url(app):
    with app.test_request_context("/", base_url="https://watchpoint.test"):
        assert normalize_next_url("//example.test/watchlist/") is None


def test_normalize_next_url_rejects_relative_path_without_leading_slash(app):
    with app.test_request_context("/", base_url="https://watchpoint.test"):
        assert normalize_next_url("watchlist/") is None


def test_current_url_for_next_uses_get_path_and_query(app):
    with app.test_request_context("/watchlist/?status=completed", method="GET"):
        assert current_url_for_next() == "/watchlist/?status=completed"


def test_current_url_for_next_uses_post_next_form_value(app):
    with app.test_request_context(
        "/reviews/42",
        method="POST",
        data={"next": "/title/42?edit_review=1"},
    ):
        assert current_url_for_next() == "/title/42?edit_review=1"


def test_current_url_for_next_falls_back_to_same_origin_referrer(app):
    with app.test_request_context(
        "/reviews/42",
        method="POST",
        base_url="https://watchpoint.test",
        headers={"Referer": "https://watchpoint.test/title/42"},
    ):
        assert current_url_for_next() == "/title/42"
