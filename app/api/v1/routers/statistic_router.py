from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.dependencies import get_uow
from app.core.auth import auth_manager
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.statistic_schema import StatisticSchema
from app.services.statistic_service import RawStatisticService
from app.utils.logger import get_logger

logger = get_logger("statistic_router")


class StatisticRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/statistics", tags=["Statistics"])
        self._register()

    def _register(self):
        self.router.post("/", response_model=StatisticSchema.Out, status_code=201)(self._create)
        self.router.get("/location/{loc_id}", response_model=list[StatisticSchema.Out])(self._list_for_location)

    # ------------------------------------------------------------------
    async def _create(
        self,
        payload: StatisticSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Creating statistic")
        return RawStatisticService(uow).create(payload, current)

    async def _list_for_location(
        self,
        loc_id: UUID,
        metric: str | None = Query(None),
        from_: datetime | None = Query(None, alias="from"),
        to: datetime | None = Query(None),
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info("Listing statistics for location")
        return RawStatisticService(uow).list_for_location(loc_id, metric, from_, to)


statistic_router = StatisticRouter().router
