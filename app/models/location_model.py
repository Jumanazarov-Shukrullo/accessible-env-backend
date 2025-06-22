import datetime as dt
import uuid
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .location_images_model import LocationImage
    from .location_inspector_model import LocationInspector
    from .rating_model import LocationRating
    from .favourite_model import Favourite
    from .review_model import Review
    from .assessment_model import LocationSetAssessment


import sqlalchemy as sa
from sqlalchemy import (
    DECIMAL,
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LocationStatus(str, PyEnum):
    old = "old"
    new = "new"
    active = "active"
    inactive = "inactive"
    under_construction = "under_construction"
    closed = "closed"


class Location(Base):
    """Core location table - normalized"""

    __tablename__ = "locations"
    __table_args__ = (
        # Add indexes for frequently queried columns
        sa.Index("idx_location_category", "category_id"),
        sa.Index("idx_location_region", "region_id"),
        sa.Index("idx_location_district", "district_id"),
        sa.Index("idx_location_city", "city_id"),
        sa.Index("idx_location_status", "status"),
        sa.Index("idx_location_coordinates", "latitude", "longitude"),
        {"extend_existing": True},
    )

    location_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    location_name: Mapped[str] = mapped_column(String[100], nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(DECIMAL(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(DECIMAL(9, 6), nullable=False)
    status: Mapped[LocationStatus] = mapped_column(
        Enum(LocationStatus), default=LocationStatus.active
    )

    # Foreign keys
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("category.category_id"), nullable=False
    )
    region_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("region.region_id"), nullable=False
    )
    district_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("district.district_id"), nullable=False
    )
    city_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("city.city_id")
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=dt.datetime.now
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=dt.datetime.now,
        onupdate=dt.datetime.now,
    )

    # Relationships
    details = relationship(
        "LocationDetails",
        back_populates="location",
        uselist=False,
        cascade="all, delete-orphan",
    )
    stats = relationship(
        "LocationStats",
        back_populates="location",
        uselist=False,
        cascade="all, delete-orphan",
    )
    images: Mapped[list["LocationImage"]] = relationship(
        back_populates="location",
        cascade="all, delete-orphan",
    )
    inspectors: Mapped[list["LocationInspector"]] = relationship(
        back_populates="location",
        cascade="all, delete-orphan",
    )
    ratings: Mapped[list["LocationRating"]] = relationship(
        back_populates="location",
        cascade="all, delete-orphan",
    )
    favourites: Mapped[list["Favourite"]] = relationship(
        back_populates="location",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="location",
        cascade="all, delete-orphan",
    )
    assessments: Mapped[list["LocationSetAssessment"]] = relationship(
        back_populates="location",
        cascade="all, delete-orphan",
    )
    category = relationship("Category")
    region = relationship("Region")
    district = relationship("District")
    city = relationship("City")


class LocationDetails(Base):
    """Location business details - normalized"""

    __tablename__ = "location_details"

    location_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("locations.location_id", ondelete="CASCADE"),
        primary_key=True,
    )
    contact_info: Mapped[str | None] = mapped_column(String[255])
    website_url: Mapped[str | None] = mapped_column(String[255])
    operating_hours: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=dt.datetime.now
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=dt.datetime.now,
        onupdate=dt.datetime.now,
    )

    # Relationships
    location = relationship("Location", back_populates="details")


class LocationStats(Base):
    """Location statistics and metrics - normalized"""

    __tablename__ = "location_stats"
    __table_args__ = {"extend_existing": True}

    location_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("locations.location_id", ondelete="CASCADE"),
        primary_key=True,
    )
    accessibility_score: Mapped[float | None] = mapped_column(DECIMAL(4, 2))
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    total_ratings: Mapped[int] = mapped_column(Integer, default=0)
    average_rating: Mapped[float | None] = mapped_column(DECIMAL(3, 2))
    last_assessment_date: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=dt.datetime.now,
        onupdate=dt.datetime.now,
    )

    # Relationships
    location = relationship("Location", back_populates="stats")
