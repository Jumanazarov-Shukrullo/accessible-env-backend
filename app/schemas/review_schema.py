import datetime as dt
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReviewSchema:
    class Create(BaseModel):
        location_id: UUID
        rating: float
        comment: Optional[str] = None
        parent_review_id: Optional[int] = None

    class Update(BaseModel):
        rating: Optional[float] = None
        comment: Optional[str] = None

    class Out(BaseModel):
        review_id: int
        user_id: UUID
        location_id: UUID
        rating: float
        comment: Optional[str]
        is_approved: bool
        parent_review_id: Optional[int]
        created_at: dt.datetime
        updated_at: dt.datetime

        model_config = ConfigDict(from_attributes=True)
