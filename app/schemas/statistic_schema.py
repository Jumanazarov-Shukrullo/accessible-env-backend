import datetime as dt
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StatisticSchema:
    class Create(BaseModel):
        location_id: UUID
        metric_type: str
        metric_value: int
        period_start: Optional[dt.datetime] = None
        period_end: Optional[dt.datetime] = None
        source: Optional[str] = None
        calculation_method: Optional[str] = None
        model_config = ConfigDict(from_attributes=True)

    class Out(Create):
        stat_id: int
        created_at: dt.datetime

        class Config:
            orm_mode = True
