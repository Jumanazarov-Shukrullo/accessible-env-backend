import time

from app.db.session import db_manager
from app.domain.unit_of_work import UnitOfWork
from app.services.notification_service import NotificationService


class NotificationDispatcher:
    def __init__(self):
        self.session = db_manager.SessionLocal

    def run_forever(self):
        while True:
            self._dispatch()
            time.sleep(10)

    def _dispatch(self):
        uow = UnitOfWork(self.session)
        # fetch unsent + send via SMTP or push (stub)
