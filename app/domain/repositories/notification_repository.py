from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import func, select, and_
from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.notification_model import Notification
from app.schemas.notification_schema import NotificationCreate


class NotificationRepository(SQLAlchemyRepository[Notification, UUID]):
    def __init__(self, db: Session):
        super().__init__(Notification, db)

    def unread_for_user(self, user_id: UUID):
        stmt = select(Notification).where(
            Notification.user_id == str(user_id), Notification.is_read is False
        )
        return self.db.scalars(stmt).all()

    def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications for a user."""
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == str(user_id), Notification.is_read is False
        )
        return self.db.scalar(stmt) or 0

    def get_user_notifications(
        self, user_id: UUID, skip: int = 0, limit: int = 20, unread_only: bool = False
    ) -> List[Notification]:
        """Get notifications for a user with pagination."""
        conditions = [Notification.user_id == str(user_id)]
        if unread_only:
            conditions.append(Notification.is_read == False)
        
        stmt = (
            select(Notification)
            .where(and_(*conditions))
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.scalars(stmt).all()

    def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Optional[Notification]:
        """Mark a notification as read."""
        stmt = select(Notification).where(
            and_(
                Notification.id == str(notification_id),
                Notification.user_id == str(user_id)
            )
        )
        notification = self.db.scalar(stmt)
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            self.db.commit()
            return notification
        return None

    def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user."""
        stmt = select(Notification).where(
            and_(
                Notification.user_id == str(user_id),
                Notification.is_read == False
            )
        )
        notifications = self.db.scalars(stmt).all()
        count = len(notifications)
        
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
        
        self.db.commit()
        return count

    def delete(self, notification_id: UUID, user_id: UUID) -> bool:
        """Delete a notification."""
        stmt = select(Notification).where(
            and_(
                Notification.id == str(notification_id),
                Notification.user_id == str(user_id)
            )
        )
        notification = self.db.scalar(stmt)
        if notification:
            self.db.delete(notification)
            self.db.commit()
            return True
        return False

    def create(self, notification_data: NotificationCreate) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=str(notification_data.user_id) if notification_data.user_id else None,
            subject=notification_data.title,
            body=notification_data.message,
            type=notification_data.notification_type,
            priority=self._priority_to_int(notification_data.priority),
            is_read=False,
            created_at=datetime.utcnow()
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def _priority_to_int(self, priority: str) -> int:
        """Convert priority string to integer."""
        priority_map = {"low": 1, "medium": 2, "high": 3}
        return priority_map.get(priority, 2)

    def mark_read(self, notif: Notification):
        notif.is_read = True
        notif.read_at = notif.read_at or datetime.utcnow()
        self.db.commit()
