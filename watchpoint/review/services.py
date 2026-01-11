from flask import g
from sqlalchemy import select, desc, asc, func, case, cast, Integer
from sqlalchemy.dialects.postgresql import insert
from review.models import Review, Vote
from db import db

REVIEW_PAGE_LIMIT = 10
REVIEW_SORT_OPTIONS = ["newest", "oldest"]


def get_reviews(page, title_id, sort_by):
    offset = (page - 1) * REVIEW_PAGE_LIMIT
    stmt = select(Review).limit(REVIEW_PAGE_LIMIT).offset(offset)
    sort_func = desc if sort_by == "newest" else asc
    stmt = stmt.order_by(sort_func("modified_at"))

    if title_id:
        stmt = stmt.filter_by(title_id=title_id)

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


def get_review_count(title_id):
    stmt = select(func.count()).select_from(Review)
    if title_id:
        stmt = stmt.filter_by(title_id=title_id)

    return db.session.scalar(stmt)


def get_title_review_by_user(title_id):
    stmt = select(Review).filter_by(title_id=title_id, user_id=g.user.id)
    review = db.session.scalar(stmt)

    return review


def upsert_review(title_id, comment, stars):
    stmt = (
        insert(Review)
        .values(title_id=title_id, user_id=g.user.id, comment=comment, stars=stars)
        .on_conflict_do_update(
            constraint="title_user_review_uc", set_=dict(comment=comment, stars=stars)
        )
    )
    db.session.execute(stmt)
    db.session.commit()


def upsert_vote(review_id, upvote):
    stmt = (
        insert(Vote)
        .values(review_id=review_id, user_id=g.user.id, upvote=upvote)
        .on_conflict_do_update(constraint="review_vote_uc", set_=dict(upvote=upvote))
    )
    db.session.execute(stmt)
    db.session.commit()
