from flask import g
from sqlalchemy import select, delete, desc, asc, func, case, cast, Integer
from sqlalchemy.dialects.postgresql import insert
from .models import Review, Vote
from ..title.models import Title
from ..db import db

REVIEW_PAGE_LIMIT = 10
REVIEW_TITLE_SEARCH_LIMIT = 10
REVIEW_SORT_OPTIONS = {
    "newest": "Newest",
    "oldest": "Oldest",
    "most_voted": "Most voted",
}


def _apply_review_filter(stmt, title_id=None, query=None, exclude_user_id=None):
    if title_id:
        stmt = stmt.where(Review.title_id == title_id)
    elif query:
        stmt = stmt.join(Title, Review.title_id == Title.id).where(
            Title.name.ilike(f"%{query}%")
        )

    if exclude_user_id is not None:
        stmt = stmt.where(Review.user_id != exclude_user_id)

    return stmt


def get_reviews(page, title_id, sort_by, query=None, exclude_user_id=None):
    offset = (page - 1) * REVIEW_PAGE_LIMIT
    stmt = select(Review).limit(REVIEW_PAGE_LIMIT).offset(offset)

    if sort_by == "most_voted":
        upvote_counts = (
            select(
                Vote.review_id,
                func.sum(case((Vote.upvote == True, 1), else_=0)).label("upvotes"),
            )
            .group_by(Vote.review_id)
            .subquery()
        )
        stmt = (
            stmt.outerjoin(upvote_counts, Review.id == upvote_counts.c.review_id)
            .order_by(
                desc(func.coalesce(upvote_counts.c.upvotes, 0)),
                desc(Review.created_at),
                desc(Review.id),
            )
        )
    else:
        sort_func = desc if sort_by == "newest" else asc
        stmt = stmt.order_by(sort_func(Review.created_at))

    stmt = _apply_review_filter(stmt, title_id, query, exclude_user_id)

    reviews = db.session.scalars(stmt).all()
    review_ids = [r.id for r in reviews]
    if not review_ids:
        return reviews

    vote_stmt = (
        select(
            Vote.review_id,
            func.sum(case((Vote.upvote == True, 1), else_=0)).label("upvotes"),
            func.sum(case((Vote.upvote == False, 1), else_=0)).label("downvotes"),
        )
        .where(Vote.review_id.in_(review_ids))
        .group_by(Vote.review_id)
    )

    if g.user:
        vote_stmt = vote_stmt.add_columns(
            func.max(
                case(
                    (Vote.user_id == g.user.id, cast(Vote.upvote, Integer)), else_=None
                )
            ).label("user_upvote")
        )

    vote_data = {row.review_id: row for row in db.session.execute(vote_stmt)}
    for r in reviews:
        r.vote_data = vote_data.get(r.id)

    return reviews


def get_review_count(title_id, query=None, exclude_user_id=None):
    stmt = select(func.count()).select_from(Review)
    stmt = _apply_review_filter(stmt, title_id, query, exclude_user_id)

    return db.session.scalar(stmt)


def get_reviewed_title_matches(query):
    stmt = (
        select(Title.id, Title.name)
        .join(Review, Review.title_id == Title.id)
        .where(Title.name.ilike(f"%{query}%"))
        .distinct()
        .order_by(Title.name.asc(), Title.id.asc())
        .limit(REVIEW_TITLE_SEARCH_LIMIT)
    )
    return [
        {"id": row.id, "name": row.name}
        for row in db.session.execute(stmt)
        if row.name
    ]


def get_title_review_by_user(title_id):
    stmt = select(Review).filter_by(title_id=title_id, user_id=g.user.id)
    review = db.session.scalar(stmt)

    return review


def upsert_review(title_id, comment, stars):
    stmt = (
        insert(Review)
        .values(title_id=title_id, user_id=g.user.id, comment=comment, stars=stars)
        .on_conflict_do_update(
            constraint="title_user_review_uc",
            set_=dict(comment=comment, stars=stars, updated_at=func.now()),
        )
    )
    db.session.execute(stmt)
    db.session.commit()


def toggle_vote(review_id, upvote):
    delete_stmt = delete(Vote).where(
        Vote.review_id == review_id,
        Vote.user_id == g.user.id,
        Vote.upvote == upvote,
    )
    result = db.session.execute(delete_stmt)
    if result.rowcount:
        db.session.commit()
        return

    stmt = (
        insert(Vote)
        .values(review_id=review_id, user_id=g.user.id, upvote=upvote)
        .on_conflict_do_update(constraint="review_vote_uc", set_=dict(upvote=upvote))
    )
    db.session.execute(stmt)
    db.session.commit()
