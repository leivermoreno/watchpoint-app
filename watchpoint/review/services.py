from flask import g
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from review.models import Review
from db import db


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
