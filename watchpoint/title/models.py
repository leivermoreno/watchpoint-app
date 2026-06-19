from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from ..db import db


class Title(db.Model):
    # JSON key -> denormalized column name. Single source of truth for the
    # projection done in from_watchmode() (and any future backfill).
    _DENORM_COLUMNS = {
        "title": "name",
        "type": "type",
        "year": "year",
        "end_year": "end_year",
        "posterLarge": "poster_large",
        "plot_overview": "plot_overview",
        "user_rating": "user_rating",
        "critic_score": "critic_score",
        "trailer": "trailer",
    }

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str | None] = mapped_column(index=True)
    type: Mapped[str | None] = mapped_column(index=True)
    year: Mapped[int | None] = mapped_column(index=True)
    end_year: Mapped[int | None]
    poster_large: Mapped[str | None]
    plot_overview: Mapped[str | None]
    user_rating: Mapped[float | None]
    critic_score: Mapped[float | None]
    trailer: Mapped[str | None]
    data: Mapped[dict] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(True), default=func.now(), onupdate=func.now()
    )

    @classmethod
    def values_from_watchmode(cls, data):
        columns = {col: data.get(key) for key, col in cls._DENORM_COLUMNS.items()}
        return {"id": data["id"], "data": data, **columns}

    @classmethod
    def watchmode_column_names(cls):
        return tuple(cls._DENORM_COLUMNS.values())

    @classmethod
    def from_watchmode(cls, data):
        return cls(**cls.values_from_watchmode(data))


class TitleSearchCache(db.Model):
    query: Mapped[str] = mapped_column(primary_key=True)
    results: Mapped[list] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(True), default=func.now())
