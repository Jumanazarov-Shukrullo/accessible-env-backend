from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AssessmentSchema:

    class Create(BaseModel):
        location_id: UUID
        set_id: int
        notes: Optional[str] = None

    class Out(BaseModel):
        assessment_id: int
        location_id: (
            str  # Will convert UUID to string automatically during validation
        )
        set_id: int
        status: str
        overall_score: Optional[float]
        assessor_id: (
            str  # Will convert UUID to string automatically during validation
        )
        notes: Optional[str]
        rejection_reason: Optional[str] = None
        assessed_at: datetime
        updated_at: Optional[datetime] = None
        submitted_at: Optional[datetime] = None
        verified_at: Optional[datetime] = None
        verifier_id: Optional[str] = None
        # Location information
        location_name: Optional[str] = None
        location_address: Optional[str] = None
        # Assessment set information
        assessment_set_name: Optional[str] = None

        model_config = ConfigDict(from_attributes=True)

        # Custom validator to convert UUIDs to strings
        @classmethod
        def model_validate(cls, obj, *args, **kwargs):
            if isinstance(obj, dict):
                obj_copy = obj.copy()
                # Convert UUIDs to strings
                if "location_id" in obj_copy and isinstance(
                    obj_copy["location_id"], UUID
                ):
                    obj_copy["location_id"] = str(obj_copy["location_id"])
                if "assessor_id" in obj_copy and isinstance(
                    obj_copy["assessor_id"], UUID
                ):
                    obj_copy["assessor_id"] = str(obj_copy["assessor_id"])
                if (
                    "verifier_id" in obj_copy
                    and obj_copy["verifier_id"] is not None
                    and isinstance(obj_copy["verifier_id"], UUID)
                ):
                    obj_copy["verifier_id"] = str(obj_copy["verifier_id"])
                return super().model_validate(obj_copy, *args, **kwargs)
            return super().model_validate(obj, *args, **kwargs)


# Accessibility Criteria Schemas
class AccessibilityCriteriaBase(BaseModel):
    criterion_name: str
    code: Optional[str] = None
    description: Optional[str] = None
    max_score: int
    unit: Optional[str] = None


class AccessibilityCriteriaCreate(AccessibilityCriteriaBase):
    pass


class AccessibilityCriteriaUpdate(BaseModel):
    criterion_name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    max_score: Optional[int] = None
    unit: Optional[str] = None


class AccessibilityCriteriaResponse(AccessibilityCriteriaBase):
    criterion_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Assessment Set Schemas
class AssessmentSetBase(BaseModel):
    set_name: str
    description: Optional[str] = None
    version: Optional[int] = 1
    is_active: Optional[bool] = True


class AssessmentSetCreate(AssessmentSetBase):
    pass


class AssessmentSetResponse(AssessmentSetBase):
    set_id: int
    created_at: datetime
    criteria: Optional[List[AccessibilityCriteriaResponse]] = None

    model_config = ConfigDict(from_attributes=True)


# Set Criteria Junction Schemas
class SetCriteriaBase(BaseModel):
    criterion_id: int
    sequence: int


class SetCriteriaCreate(SetCriteriaBase):
    pass


class SetCriteriaResponse(SetCriteriaBase):
    set_id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Added schema for nested location information in assessment responses
class AssessmentLocationInfo(BaseModel):
    location_id: UUID
    location_name: str
    address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Location Set Assessment Schemas
class LocationSetAssessmentBase(BaseModel):
    set_id: int
    notes: Optional[str] = None
    verified: Optional[bool] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[UUID] = None
    rejection_reason: Optional[str] = None
    location_info: Optional[AssessmentLocationInfo] = (
        None  # Added field for location details
    )
    details: Optional[List[Any]] = (
        None  # Will be populated with LocationAssessmentResponse objects
    )

    model_config = ConfigDict(from_attributes=True)


class LocationSetAssessmentCreate(LocationSetAssessmentBase):
    set_id: int
    notes: Optional[str] = None
    criterion_ids: Optional[List[int]] = (
        None  # Optional list of specific criteria to include
    )


class LocationSetAssessmentResponse(LocationSetAssessmentBase):
    assessment_id: int
    location_id: UUID
    assessor_id: UUID
    overall_score: Optional[float] = None
    status: str = "pending"
    assessed_at: datetime
    updated_at: datetime
    verified: Optional[bool] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[UUID] = None
    rejection_reason: Optional[str] = None
    location_info: Optional[AssessmentLocationInfo] = (
        None  # Added field for location details
    )
    details: Optional[List[Any]] = (
        None  # Will be populated with LocationAssessmentResponse objects
    )
    submitted_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# Location Assessment Detail Schemas
class LocationAssessmentBase(BaseModel):
    criterion_id: int
    score: int
    condition: Optional[str] = None
    comment: Optional[str] = None


class LocationAssessmentCreate(LocationAssessmentBase):
    pass


class LocationAssessmentResponse(LocationAssessmentBase):
    assessment_detail_id: int
    location_set_assessment_id: int
    is_reviewed: bool = False
    criterion: Optional[AccessibilityCriteriaResponse] = (
        None  # To include criterion details
    )

    model_config = ConfigDict(from_attributes=True)


# Assessment Verification Schemas
class AssessmentVerificationBase(BaseModel):
    is_verified: bool
    comment: Optional[str] = None


class AssessmentVerificationCreate(AssessmentVerificationBase):
    pass


class AssessmentVerificationResponse(AssessmentVerificationBase):
    verification_id: int
    location_set_assessment_id: int
    verifier_id: UUID
    verified_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Assessment Comment Schemas
class AssessmentCommentBase(BaseModel):
    comment_text: str


class AssessmentCommentCreate(AssessmentCommentBase):
    pass


class AssessmentCommentResponse(AssessmentCommentBase):
    comment_id: int
    user_id: UUID
    location_set_assessment_id: int
    is_edited: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Image Schemas for Assessment
class AssessmentImageBase(BaseModel):
    image_url: str
    description: Optional[str] = None


class AssessmentImageCreate(AssessmentImageBase):
    assessment_detail_id: int


class AssessmentImageResponse(AssessmentImageBase):
    image_id: int
    assessment_detail_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
