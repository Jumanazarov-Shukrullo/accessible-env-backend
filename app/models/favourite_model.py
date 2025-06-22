import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Favourite(Base):
    __tablename__ = "favourites"
    __table_args__ = {"extend_existing": True}

    favorite_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"))
    location_id: Mapped[str] = mapped_column(
        String, ForeignKey("locations.location_id")
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=dt.datetime.utcnow
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
    )

    # Relationships
    user = relationship("User", back_populates="favourites")
    location = relationship("Location", back_populates="favourites")
