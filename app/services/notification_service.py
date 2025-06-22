from uuid import UUID

from app.domain.unit_of_work import UnitOfWork
from app.models.notification_model import Notification
from app.models.user_model import User
from app.schemas.notification_schema import NotificationCreate


class NotificationService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def send(self, payload: NotificationCreate) -> Notification:
        with self.uow:
            notif = self.uow.notifications.add(
                Notification(**payload.dict(), status_id=1)
            )  # "new" status (assumed)
            self.uow.commit()
            # background task (email, push) could be queued here
            return notif

    def unread_for_user(self, user_id: UUID):
        return self.uow.notifications.unread_for_user(user_id)

    def mark_read(self, notif_id: UUID, user: User):
        with self.uow:
            notif = self.uow.notifications.get(str(notif_id))
            if notif and notif.user_id == str(user.user_id):
                self.uow.notifications.mark_read(notif)
                self.uow.commit()
                return notif
            raise ValueError("Not found or forbidden")
