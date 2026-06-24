from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(True), default=func.now(), sort_order=100
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(True), default=func.now(), onupdate=func.now(), sort_order=101
    )
