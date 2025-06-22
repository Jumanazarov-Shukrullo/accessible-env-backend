import datetime as dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .district_model import District

from sqlalchemy import DECIMAL, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base



class Region(Base):
    __tablename__ = "region"
    region_id: Mapped[int] = mapped_column(primary_key=True)
    region_name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    region_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    description: Mapped[str | None]
    area: Mapped[float | None] = mapped_column(DECIMAL(10, 2))
    population: Mapped[int | None]

    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)

    districts: Mapped[list["District"]] = relationship(
        back_populates="region", cascade="all,delete"
    )
