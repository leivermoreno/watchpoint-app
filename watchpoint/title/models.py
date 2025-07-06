from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column
from db import db


class Title(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
