from flask import g
from sqlalchemy import select, desc, func
from sqlalchemy.dialects.postgresql import insert
from review.models import Review
from db import db

REVIEW_PAGE_LIMIT = 10


def get_reviews(page, title_id):
    offset = (page - 1) * REVIEW_PAGE_LIMIT
    stmt = (
        select(Review)
        .order_by(desc("modified_at"))
        .limit(REVIEW_PAGE_LIMIT)
        .offset(offset)
    )
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
