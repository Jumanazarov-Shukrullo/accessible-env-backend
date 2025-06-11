import datetime as dt
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Review(Base):
    """Core reviews table - normalized"""
    __tablename__ = "reviews"
    __table_args__ = {"extend_existing": True}

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    location_id: Mapped[str] = mapped_column(String, ForeignKey("locations.location_id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[float] = mapped_column(DECIMAL(3, 2), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    parent_review_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("reviews.review_id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="reviews")
    location = relationship("Location", back_populates="reviews")
    review_metadata = relationship("ReviewMetadata", back_populates="review", uselist=False, cascade="all, delete-orphan")
    parent_review = relationship("Review", remote_side="Review.review_id")
    replies = relationship("Review", remote_side="Review.parent_review_id", cascade="all, delete-orphan", overlaps="parent_review")


class ReviewMetadata(Base):
    """Review metadata for performance optimization"""
    __tablename__ = "review_metadata"
    __table_args__ = {"extend_existing": True}

    review_id: Mapped[int] = mapped_column(Integer, ForeignKey("reviews.review_id", ondelete="CASCADE"), primary_key=True)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    report_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text)
    moderation_status: Mapped[str] = mapped_column(String(50), default="approved", nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.user_id"))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    # Relationships
    review = relationship("Review", back_populates="review_metadata")
    moderator = relationship("User")
