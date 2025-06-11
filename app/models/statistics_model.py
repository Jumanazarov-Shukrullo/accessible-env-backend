import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Statistic(Base):
    """
    Stores aggregated metric values for a location and a period.
    """

    __tablename__ = "statistics"
    __table_args__ = (
        Index(
            "ix_statistics_loc_metric_period",
            "location_id",
            "metric_type",
            "period_start",
            "period_end",
        ),
    )

    stat_id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.location_id"))
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_value: Mapped[int | None]
    source: Mapped[str | None]
    calculation_method: Mapped[str | None]

    period_start: Mapped[dt.datetime | None]
    period_end: Mapped[dt.datetime | None]

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=dt.datetime.utcnow)

    location = relationship("Location")
