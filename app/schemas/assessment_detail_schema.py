import datetime as dt
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DetailSchema:
    class Base(BaseModel):
        location_set_assessment_id: int
        criterion_id: int
        score: float = Field(ge=0)
        condition: Optional[str] = None
        comment: Optional[str] = None

    class Create(Base):
        pass

    class Update(BaseModel):
        score: Optional[float] = Field(default=None, ge=0)
        condition: Optional[str] = None
        comment: Optional[str] = None
        admin_comments: Optional[str] = None

    class AdminReview(BaseModel):
        comment: str

    class Out(Base):
        assessment_detail_id: int
        is_reviewed: bool
        admin_comments: Optional[str] = None
        is_corrected: Optional[bool] = False
        images: Optional[List["ImageSchema.Out"]] = None
        created_at: Optional[dt.datetime] = None
        updated_at: Optional[dt.datetime] = None

        model_config = ConfigDict(from_attributes=True)


class ImageSchema:
    class Base(BaseModel):
        assessment_detail_id: int
        image_url: str
        description: Optional[str] = None

    class PresignRequest(BaseModel):
        assessment_detail_id: int
        filename: str

    class Create(Base):
        pass

    class Out(Base):
        image_id: int
        uploaded_at: dt.datetime

        model_config = ConfigDict(from_attributes=True)


class VerificationSchema:
    class Base(BaseModel):
        location_set_assessment_id: int
        is_verified: bool
        comment: Optional[str] = None

    class Create(Base):
        pass

    class Out(Base):
        verification_id: int
        verifier_id: UUID
        verified_at: dt.datetime

        model_config = ConfigDict(from_attributes=True)


class CommentSchema:
    class Base(BaseModel):
        assessment_detail_id: int
        comment: str

    class Create(Base):
        pass

    class Out(BaseModel):
        comment_id: int
        author_id: UUID
        comment: str
        created_at: dt.datetime
        is_edited: Optional[bool] = False

        model_config = ConfigDict(from_attributes=True)


# Add this at the bottom to resolve the forward reference
DetailSchema.Out.model_rebuild()
