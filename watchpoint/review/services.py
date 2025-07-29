from flask import g
from sqlalchemy import select, desc, asc, func
from sqlalchemy.dialects.postgresql import insert
from review.models import Review, Vote
from db import db

REVIEW_PAGE_LIMIT = 10
REVIEW_SORT_OPTIONS = ["newest", "oldest"]


def get_reviews(page, title_id, sort_by):
    print(sort_by)
    offset = (page - 1) * REVIEW_PAGE_LIMIT
    stmt = select(Review).limit(REVIEW_PAGE_LIMIT).offset(offset)
    sort_func = desc if sort_by == "newest" else asc
    stmt = stmt.order_by(sort_func("modified_at"))

    if title_id:
        stmt = stmt.filter_by(title_id=title_id)

    result = db.session.scalars(stmt).all()

    return result


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
