from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_uow
from app.core.auth import auth_manager
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.notification_schema import (
    NotificationCreate,
    NotificationResponse,
)
from app.services.notification_service import NotificationService
from app.utils.logger import get_logger


logger = get_logger("notification_router")


class NotificationRouter:
    def __init__(self):
        self.router = APIRouter(
            prefix="/notifications", tags=["Notifications"]
        )
        self._register()

    def _register(self):
        self.router.post(
            "/", response_model=NotificationResponse, status_code=201
        )(self._send)
        self.router.get("/unread", response_model=list[NotificationResponse])(
            self._unread
        )
        self.router.post(
            "/{notif_id}/read", response_model=NotificationResponse
        )(self._mark_read)
        self.router.get("/")(self._get_notifications)
        self.router.post("/")(self._create_notification)
        self.router.delete("/{notification_id}")(self._delete_notification)

    async def _send(
        self,
        payload: NotificationCreate,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Sending notification")
        return NotificationService(uow).send(payload)

    async def _unread(
        self,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Fetching unread notifications for user")
        return NotificationService(uow).unread_for_user(current.user_id)

    async def _mark_read(
        self,
        notif_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Marking notification as read")
        return NotificationService(uow).mark_read(notif_id, current)

    async def _get_notifications(
        self, _: User = Depends(auth_manager.get_current_user)
    ):
        logger.info("Fetching all notifications")
        return {"notifications": []}

    async def _create_notification(
        self, current: User = Depends(auth_manager.get_current_user)
    ):
        logger.info("Creating new notification")
        return {"message": "Notification created"}

    async def _delete_notification(
        self,
        notification_id: UUID,
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Deleting notification")
        return {"message": "Notification deleted"}


notification_router = NotificationRouter().router
