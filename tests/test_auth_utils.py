from watchpoint.auth.utils import current_url_for_next, normalize_next_url


TEST_BASE_URL = "https://watchpoint.test"
WATCHLIST_PENDING_URL = "/watchlist/?status=pending"
WATCHLIST_COMPLETED_URL = "/watchlist/?status=completed"
TITLE_URL = "/title/42"
TITLE_REVIEWS_URL = "/title/42?tab=reviews"
TITLE_EDIT_REVIEW_URL = "/title/42?edit_review=1"
REVIEW_URL = "/reviews/42"


def test_normalize_next_url_accepts_safe_local_urls(app):
    with app.test_request_context("/", base_url=TEST_BASE_URL):
        assert normalize_next_url(WATCHLIST_PENDING_URL) == WATCHLIST_PENDING_URL
        assert normalize_next_url(f"{TEST_BASE_URL}{TITLE_REVIEWS_URL}") == TITLE_REVIEWS_URL


def test_normalize_next_url_rejects_unsafe_or_invalid_urls(app):
    with app.test_request_context("/", base_url=TEST_BASE_URL):
        for target in (
            "https://example.test/watchlist/",
            "//example.test/watchlist/",
            "watchlist/",
        ):
            assert normalize_next_url(target) is None, target


def test_current_url_for_next_uses_get_path_and_query(app):
    with app.test_request_context(WATCHLIST_COMPLETED_URL, method="GET"):
        assert current_url_for_next() == WATCHLIST_COMPLETED_URL


def test_current_url_for_next_uses_post_next_form_value(app):
    with app.test_request_context(
        REVIEW_URL,
        method="POST",
        data={"next": TITLE_EDIT_REVIEW_URL},
    ):
        assert current_url_for_next() == TITLE_EDIT_REVIEW_URL


def test_current_url_for_next_falls_back_to_safe_referrer(app):
    with app.test_request_context(
        REVIEW_URL,
        method="POST",
        base_url=TEST_BASE_URL,
        headers={"Referer": f"{TEST_BASE_URL}{TITLE_URL}"},
    ):
        assert current_url_for_next() == TITLE_URL
