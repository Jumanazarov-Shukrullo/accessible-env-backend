from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.notification_model import Notification


class NotificationRepository(SQLAlchemyRepository[Notification, UUID]):
    def __init__(self, db: Session):
        super().__init__(Notification, db)

    def unread_for_user(self, user_id: UUID):
        stmt = select(Notification).where(
            Notification.user_id == str(user_id), Notification.is_read is False
        )
        return self.db.scalars(stmt).all()

    def mark_read(self, notif: Notification):
        notif.is_read = True
        notif.read_at = notif.read_at or self.db.bind.scalar(
            "SELECT NOW()"
        )  # quick
