import datetime as dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .region_model import Region
    from .city_model import City

from sqlalchemy import DECIMAL, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.db.base import Base


class District(Base):
    __tablename__ = "district"
    district_id: Mapped[int] = mapped_column(primary_key=True)
    district_name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    district_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    description: Mapped[str | None]
    area: Mapped[float | None] = mapped_column(DECIMAL(10, 2))
    population: Mapped[int | None]

    region_id: Mapped[int] = mapped_column(ForeignKey("region.region_id"))
    region: Mapped["Region"] = relationship(back_populates="districts")

    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)

    cities: Mapped[list["City"]] = relationship(
        back_populates="district", cascade="all,delete"
    )
