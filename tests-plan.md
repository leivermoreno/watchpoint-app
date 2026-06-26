# Tests Plan

Build coverage in small layers, from cheap unit tests to heavier integration
tests. Keep early slices database-free and network-free.

## 1. Finish Auth Helper Tests

- [x] Add basic `auth.utils` coverage:
  - [x] Safe local `next` URLs are accepted.
  - [x] Unsafe external URLs are rejected.
  - [x] GET requests use the current path and query as `next`.
  - [x] POST requests prefer a safe submitted `next`.
- [x] Add remaining `auth.utils` edge cases:
  - [x] Empty `next` returns `None`.
  - [x] Bad POST `next` falls back to a safe referrer.
  - [x] External referrer is rejected.
- [x] Add `login_required` behavior:
  - [x] Unauthenticated users redirect to login with a safe `next`.
  - [x] Authenticated users call the wrapped view.

## 2. Test Title Search Route Logic Without DB or Network

- [x] Test `search_results_context()` for:
  - [x] Short query.
  - [x] Too-long query.
  - [x] Valid result.
  - [x] Watchmode `503` fallback message.
- [x] Test `index()` HTMX behavior, especially empty query setting
  `HX-Replace-Url`.
- [x] Monkeypatch `get_autocomplete_titles`; do not call Watchmode.

## 3. Test Title Service Logic Without DB or Network

- [x] `Title.values_from_watchmode()`.
- [x] `_is_fresh()` with timezone-aware and naive timestamps.
- [x] `get_sources()` filtering:
  - [x] US-only rows.
  - [x] Duplicate providers.
  - [x] Malformed rows.
- [x] `get_title_data()` rejecting bad or mismatched IDs and using fallback sources.
- [x] `get_title_info_or_404()` cache behavior:
  - [x] Fresh cached title skips Watchmode.
  - [x] Stale cached title falls back to cached data when refresh fails.
- [x] `get_autocomplete_titles()` cache behavior:
  - [x] Fresh cached search returns immediately.
  - [x] Stale cached search falls back to cached results when Watchmode fails.

## 4. Test Forms and Model Methods

- [x] `User.set_password()` and `User.check_password()`.
- [x] Confirm passwords are not stored as plaintext.
- [x] `ReviewForm` validation for comment length and required stars.
- [x] `ReviewForm` coercion of `stars` to `int`.
- [x] `ReviewForm` rejects out-of-range stars.
- [x] Do not add broad auth form length tests unless those forms get custom logic;
  they mostly retest WTForms validators.

## 5. Add Thin Route Tests With Monkeypatching

- [x] `watchlist.get_watchlist()`:
  - [x] Normalizes invalid status values to `all`.
  - [x] Passes `None` to the service for the all-list view.
- [x] `watchlist.modify_watchlist()`:
  - [x] Calls `upsert_watchlist` for valid statuses.
  - [x] Calls `remove_watchlist` for empty status.
  - [x] Flashes a warning for invalid status.
- [x] `review.create_review()`:
  - [x] Valid form calls `upsert_review`.
  - [x] Invalid form re-renders the title page through `render_title_info`.
- [x] `review.vote_review()`:
  - [x] Rejects bad vote values.
  - [x] Calls `toggle_vote`.
  - [x] Respects a safe `next`.
- [x] `review.show_reviews()`:
  - [x] Normalizes invalid page values.
  - [x] Normalizes invalid sort values.
  - [x] Handles too-long queries.
- [x] Keep these mostly DB-free by monkeypatching service calls and template
  rendering.

## 6. Add PostgreSQL Integration Tests

Do not use SQLite for these. The app uses PostgreSQL `JSONB` and
PostgreSQL-specific `ON CONFLICT` upserts, so SQLite tests would verify different
behavior.

- [x] Add a real `create_app()` fixture with:
  - [x] Test environment variables.
  - [x] `WTF_CSRF_ENABLED = False`.
  - [x] A separate test PostgreSQL database.
- [x] Cover:
  - [x] Auth signup and login.
  - [x] Title upsert and search-cache upsert.
  - [x] Title/search cache fallback behavior where unit tests cannot cover the
    database constraint/update semantics.
  - [x] Watchlist upsert and remove.
  - [x] Review upsert.
  - [x] Vote toggle.
  - [x] Review sorting and counts.
- [x] Keep this slice small. It should prove the PostgreSQL-specific schema and
  upsert behavior, not duplicate every route test.

## Suggested Next Slice

Add a PostgreSQL migration smoke test if you want coverage for Alembic upgrade
files in addition to the model-created schema used by the integration tests.

## Running Tests

Install development dependencies, then run pytest:

```sh
pip install -r requirements-dev.txt
pytest
```

PostgreSQL integration tests require an explicit throwaway database URI. The
database name must include `test` because the fixture drops and recreates tables:

```sh
export WATCHPOINT_TEST_DATABASE_URI=postgresql+psycopg2://user:pass@localhost:5432/watchpoint_test
```
