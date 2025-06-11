import datetime as dt
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AssessmentHeaderOut(BaseModel):
    assessment_id: int
    location_id: UUID
    status: str
    overall_score: float | None
    assessed_at: dt.datetime
    submitted_at: dt.datetime | None
    verified_at: dt.datetime | None

    model_config = ConfigDict(from_attributes=True)


class SetCriteriaResponse(BaseModel):
    set_id: int
    criterion_id: int
    sequence: int
    criterion_name: str
    code: str
    description: Optional[str] = None
    max_score: int
    unit: Optional[str] = None
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class AssessmentSetResponse(BaseModel):
    set_id: int
    set_name: str
    description: Optional[str] = None
    version: int
    is_active: bool
    created_at: dt.datetime
    criteria: List[SetCriteriaResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AssessmentSetCreate(BaseModel):
    set_name: str
    description: Optional[str] = None
    version: int = 1
    is_active: bool = True


class SetCriteriaCreate(BaseModel):
    criterion_id: int
    sequence: int


class LocationSetAssessmentCreate(BaseModel):
    """Schema for creating a new location set assessment"""

    location_id: Optional[UUID] = None
    set_id: int
    notes: Optional[str] = None


class AssessmentSetSchema:
    """Namespace for assessment set schemas"""

    class Create(BaseModel):
        set_name: str
        description: Optional[str] = None
        version: int = 1
        is_active: bool = True

    class Update(BaseModel):
        set_name: str
        description: Optional[str] = None
        version: int = 1
        is_active: bool = True

    class Response(BaseModel):
        set_id: int
        set_name: str
        description: Optional[str] = None
        version: int
        is_active: bool
        created_at: dt.datetime

        model_config = ConfigDict(from_attributes=True)

    class Criterion(BaseModel):
        criterion_id: int
        sequence: int
