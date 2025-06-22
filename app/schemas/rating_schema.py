import datetime as dt
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RatingBase(BaseModel):
    rating: float = Field(
        ..., ge=1.0, le=5.0, description="Rating from 1.0 to 5.0"
    )
    comment: Optional[str] = Field(
        None, max_length=1000, description="Optional comment"
    )


class RatingCreate(RatingBase):
    location_id: UUID


class RatingUpdate(BaseModel):
    rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    comment: Optional[str] = Field(None, max_length=1000)


class RatingOut(RatingBase):
    rating_id: int
    location_id: UUID
    user_id: UUID
    created_at: dt.datetime
    updated_at: dt.datetime

    # User info
    user_name: Optional[str] = None
    user_full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LocationRatingStats(BaseModel):
    location_id: UUID
    average_rating: float
    total_ratings: int
    rating_distribution: dict[
        str, int
    ]  # {"1": 5, "2": 10, "3": 20, "4": 30, "5": 35}

    model_config = ConfigDict(from_attributes=True)
