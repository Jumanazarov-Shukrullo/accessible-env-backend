import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LocationInspectorOut(BaseModel):
    user_id: UUID
    assigned_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)
