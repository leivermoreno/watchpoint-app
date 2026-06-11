from typing import List
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from ..db import db, TimestampMixin


class User(TimestampMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    nickname: Mapped[str] = mapped_column(String(50), unique=True)
    _password: Mapped[str] = mapped_column("password_hash", String(255))
    watchlist: Mapped[List["Watchlist"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    reviews: Mapped[List["Review"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    votes: Mapped[List["Vote"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )

    def set_password(self, password):
        self._password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self._password, password)
