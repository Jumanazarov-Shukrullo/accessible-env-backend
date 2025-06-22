import datetime as dt
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LocationRating(Base):
    __tablename__ = "location_ratings"

    rating_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    location_id: Mapped[str] = mapped_column(
        String, ForeignKey("locations.location_id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.user_id"), nullable=False
    )
    rating: Mapped[float] = mapped_column(Float, nullable=False)  # 1.0 to 5.0
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=dt.datetime.utcnow
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
    )

    # Relationships
    location = relationship("Location", back_populates="ratings")
    user = relationship("User", back_populates="ratings")

    def __repr__(self):
        return f"<LocationRating(rating_id={
            self.rating_id}, location_id={
            self.location_id}, user_id={
            self.user_id}, rating={
                self.rating})>"
