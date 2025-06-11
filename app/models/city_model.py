import datetime as dt

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class City(Base):
    __tablename__ = "city"
    city_id: Mapped[int] = mapped_column(primary_key=True)
    city_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    city_code: Mapped[str | None] = mapped_column(String(20), unique=True)

    region_id: Mapped[int] = mapped_column(ForeignKey("region.region_id"))
    district_id: Mapped[int] = mapped_column(ForeignKey("district.district_id"))

    region: Mapped["Region"] = relationship()
    district: Mapped["District"] = relationship(back_populates="cities")

    population: Mapped[int | None]
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)
