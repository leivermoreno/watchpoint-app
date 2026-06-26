from watchpoint.title.blueprint import autocomplete_result_titles
from watchpoint.title.services import (
    SEARCH_MAX_LENGTH,
    SEARCH_MIN_LENGTH,
    clean_search_query,
    normalize_search_query,
    search_query_length_error,
)


def test_clean_search_query_collapses_whitespace():
    assert clean_search_query("  The   Matrix \n Reloaded  ") == "The Matrix Reloaded"


def test_search_query_length_error_rejects_short_queries():
    error, message = search_query_length_error("x" * (SEARCH_MIN_LENGTH - 1))

    assert error == "too_short"
    assert message == f"Search must be at least {SEARCH_MIN_LENGTH} characters"


def test_search_query_length_error_rejects_long_queries():
    error, message = search_query_length_error("x" * (SEARCH_MAX_LENGTH + 1))

    assert error == "too_long"
    assert message == f"Search must be {SEARCH_MAX_LENGTH} characters or fewer"


def test_search_query_length_error_allows_valid_queries():
    assert search_query_length_error("x" * SEARCH_MIN_LENGTH) == (None, None)
    assert search_query_length_error("x" * SEARCH_MAX_LENGTH) == (None, None)


def test_normalize_search_query_cleans_and_casefolds():
    assert normalize_search_query("  The   MATRIX  ") == "the matrix"


def test_autocomplete_result_titles_keeps_only_valid_id_and_name_pairs():
    titles = [
        {"id": "42", "name": "Heat"},
        {"id": "not-an-int", "name": "Bad ID"},
        {"name": "Missing ID"},
        {"id": 7, "name": ""},
        {"id": 8},
        None,
        {"id": 99, "name": "Alien"},
    ]

    assert autocomplete_result_titles(titles) == [
        {"id": 42, "name": "Heat"},
        {"id": 99, "name": "Alien"},
    ]
