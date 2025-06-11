from datetime import datetime
from uuid import UUID

from fastapi import HTTPException

from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.statistic_schema import StatisticSchema


class RawStatisticService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def create(self, payload: StatisticSchema.Create, user: User):
        # only admin can create statistics by hand
        self._require_admin(user)
        with self.uow:
            stat = self.uow.statistics.add(self.uow.statistics.model(**payload.dict()))
            self.uow.commit()
            return stat

    def list_for_location(
        self, loc_id: UUID, metric: str | None, period_from: datetime | None, period_to: datetime | None
    ):
        return self.uow.statistics.list_for_location(loc_id, metric, period_from, period_to)

    def _require_admin(self, user: User):
        if user.role_id not in (1, 2):
            raise HTTPException(403, "Admin only")
