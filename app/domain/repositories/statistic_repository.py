from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.statistics_model import Statistic


class StatisticRepository(SQLAlchemyRepository[Statistic, int]):
    def __init__(self, db: Session):
        super().__init__(Statistic, db)

    def list_for_location(
        self,
        loc_id: UUID,
        metric: str | None = None,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
    ):
        stmt = select(Statistic).where(Statistic.location_id == str(loc_id))
        if metric:
            stmt = stmt.where(Statistic.metric_type == metric)
        if period_from and period_to:
            stmt = stmt.where(
                and_(
                    Statistic.period_start >= period_from,
                    Statistic.period_end <= period_to,
                )
            )
        return self.db.scalars(stmt).all()
