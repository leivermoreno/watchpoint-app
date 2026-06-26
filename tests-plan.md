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

- `Title.values_from_watchmode()`.
- `_is_fresh()` with timezone-aware and naive timestamps.
- `get_sources()` filtering:
  - US-only rows.
  - Duplicate providers.
  - Malformed rows.
- `get_title_data()` rejecting bad or mismatched IDs and using fallback sources.
- `get_title_info_or_404()` cache behavior:
  - Fresh cached title skips Watchmode.
  - Stale cached title falls back to cached data when refresh fails.
- `get_autocomplete_titles()` cache behavior:
  - Fresh cached search returns immediately.
  - Stale cached search falls back to cached results when Watchmode fails.

## 4. Test Forms and Model Methods

- `User.set_password()` and `User.check_password()`.
- Confirm passwords are not stored as plaintext.
- `ReviewForm` validation for comment length and required stars.
- `ReviewForm` coercion of `stars` to `int`.
- `ReviewForm` rejects out-of-range stars.
- Do not add broad auth form length tests unless those forms get custom logic;
  they mostly retest WTForms validators.

## 5. Add Thin Route Tests With Monkeypatching

- `watchlist.get_watchlist()`:
  - Normalizes invalid status values to `all`.
  - Passes `None` to the service for the all-list view.
- `watchlist.modify_watchlist()`:
  - Calls `upsert_watchlist` for valid statuses.
  - Calls `remove_watchlist` for empty status.
  - Flashes a warning for invalid status.
- `review.create_review()`:
  - Valid form calls `upsert_review`.
  - Invalid form re-renders the title page through `render_title_info`.
- `review.vote_review()`:
  - Rejects bad vote values.
  - Calls `toggle_vote`.
  - Respects a safe `next`.
- `review.show_reviews()`:
  - Normalizes invalid page values.
  - Normalizes invalid sort values.
  - Handles too-long queries.
- Keep these mostly DB-free by monkeypatching service calls and template
  rendering.

## 6. Add PostgreSQL Integration Tests

Do not use SQLite for these. The app uses PostgreSQL `JSONB` and
PostgreSQL-specific `ON CONFLICT` upserts, so SQLite tests would verify different
behavior.

- Add a real `create_app()` fixture with:
  - Test environment variables.
  - `WTF_CSRF_ENABLED = False`.
  - A separate test PostgreSQL database.
- Cover:
  - Auth signup and login.
  - Title upsert and search-cache upsert.
  - Title/search cache fallback behavior where unit tests cannot cover the
    database constraint/update semantics.
  - Watchlist upsert and remove.
  - Review upsert.
  - Vote toggle.
  - Review sorting and counts.
- Keep this slice small. It should prove the PostgreSQL-specific schema and
  upsert behavior, not duplicate every route test.

## Suggested Next Slice

Test title service logic without DB or network by monkeypatching database and
Watchmode calls while covering the service behavior listed in slice 3.

## Running Tests

Install development dependencies, then run pytest:

```sh
pip install -r requirements-dev.txt
pytest
```
