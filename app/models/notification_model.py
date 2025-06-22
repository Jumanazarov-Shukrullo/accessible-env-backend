import datetime as dt
import uuid
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NotificationType(str, PyEnum):
    assessment_verified = "assessment_verified"
    assessment_rejected = "assessment_rejected"
    location_approved = "location_approved"
    location_rejected = "location_rejected"
    user_registered = "user_registered"
    password_reset = "password_reset"
    system_maintenance = "system_maintenance"


class NotificationStatus(str, PyEnum):
    pending = "pending"
    sent = "sent"
    read = "read"
    expired = "expired"
    failed = "failed"


class Notification(Base):
    """Simplified notifications table with embedded type and status"""

    __tablename__ = "notifications"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus),
        default=NotificationStatus.pending,
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[Optional[str]] = mapped_column(String(255))
    priority: Mapped[Optional[int]] = mapped_column(Integer)
    expires_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=dt.datetime.utcnow
    )
    sent_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    read_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    notification_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    deleted_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    # Relationships
    user = relationship("User", back_populates="notifications")
