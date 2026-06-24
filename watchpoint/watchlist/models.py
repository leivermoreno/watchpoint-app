from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import TimestampMixin, db

if TYPE_CHECKING:
    from ..title.models import Title

WATCHLIST_CHOICES = ("pending", "completed", "favorites")


class Watchlist(TimestampMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("title.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(
            *WATCHLIST_CHOICES,
            name="watchlist_enum",
            native_enum=False,
            create_constraint=True,
        )
    )
    title: Mapped["Title"] = relationship()
    __table_args__ = (
        UniqueConstraint("title_id", "user_id", name="title_user_watchlist_uc"),
    )
