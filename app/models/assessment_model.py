from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class AssessmentStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    verified = "verified"
    rejected = "rejected"
    archived = "archived"
    pending = "pending"


class AccessibilityCriteria(Base):
    __tablename__ = "accessibility_criteria"
    __table_args__ = {"extend_existing": True}

    criterion_id = Column(Integer, primary_key=True, index=True)
    criterion_name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    max_score = Column(Integer, nullable=False)
    unit = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    set_criteria = relationship("SetCriteria", back_populates="criteria")
    assessments = relationship("LocationAssessment", back_populates="criteria")


class AssessmentSet(Base):
    __tablename__ = "assessment_sets"
    __table_args__ = {"extend_existing": True}

    set_id = Column(Integer, primary_key=True, index=True)
    set_name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    set_criteria = relationship("SetCriteria", back_populates="assessment_set")
    location_assessments = relationship(
        "LocationSetAssessment", back_populates="assessment_set"
    )


class SetCriteria(Base):
    __tablename__ = "set_criteria"
    __table_args__ = {"extend_existing": True}

    set_id = Column(
        Integer, ForeignKey("assessment_sets.set_id"), primary_key=True
    )
    criterion_id = Column(
        Integer,
        ForeignKey("accessibility_criteria.criterion_id"),
        primary_key=True,
    )
    sequence = Column(Integer, nullable=False)

    # Relationships
    assessment_set = relationship(
        "AssessmentSet", back_populates="set_criteria"
    )
    criteria = relationship(
        "AccessibilityCriteria", back_populates="set_criteria"
    )


class LocationSetAssessment(Base):
    """Main assessment table with embedded verification data"""

    __tablename__ = "location_set_assessments"
    __table_args__ = {"extend_existing": True}

    assessment_id = Column(Integer, primary_key=True, index=True)
    location_id = Column(
        String, ForeignKey("locations.location_id"), nullable=False
    )
    set_id = Column(
        Integer, ForeignKey("assessment_sets.set_id"), nullable=False
    )
    assessor_id = Column(String, ForeignKey("users.user_id"), nullable=False)

    # Embedded verification fields (no separate table)
    verifier_id = Column(String, ForeignKey("users.user_id"), nullable=True)
    is_verified = Column(Boolean, nullable=True)
    verified_comment = Column(Text, nullable=True)
    verified_at = Column(DateTime, nullable=True)

    status = Column(
        String(50), default=AssessmentStatus.draft.value, nullable=False
    )
    overall_score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    assessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    submitted_at = Column(DateTime, nullable=True)

    # Relationships
    location = relationship("Location", back_populates="assessments")
    assessment_set = relationship(
        "AssessmentSet", back_populates="location_assessments"
    )
    assessor = relationship(
        "User", foreign_keys=[assessor_id], overlaps="assessments"
    )
    verifier = relationship(
        "User", foreign_keys=[verifier_id], overlaps="verifications"
    )
    assessment_details = relationship(
        "LocationAssessment",
        back_populates="location_set_assessment",
        cascade="all, delete-orphan",
    )
    assessment_images = relationship(
        "AssessmentImage",
        back_populates="location_set_assessment",
        cascade="all, delete-orphan",
    )
    assessment_comments = relationship(
        "AssessmentComment",
        back_populates="location_set_assessment",
        cascade="all, delete-orphan",
    )


class LocationAssessment(Base):
    __tablename__ = "location_assessments"
    __table_args__ = {"extend_existing": True}

    assessment_detail_id = Column(Integer, primary_key=True, index=True)
    location_set_assessment_id = Column(
        Integer,
        ForeignKey("location_set_assessments.assessment_id"),
        nullable=False,
    )
    criterion_id = Column(
        Integer,
        ForeignKey("accessibility_criteria.criterion_id"),
        nullable=False,
    )
    score = Column(Integer, nullable=False)
    condition = Column(Text)
    comment = Column(Text)
    admin_comments = Column(Text)
    is_reviewed = Column(Boolean, default=False, nullable=False)
    # Marked by admin when user fixes the issue pointed in assessment
    is_corrected = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    location_set_assessment = relationship(
        "LocationSetAssessment", back_populates="assessment_details"
    )
    criteria = relationship(
        "AccessibilityCriteria", back_populates="assessments"
    )
    assessment_images = relationship(
        "AssessmentImage",
        back_populates="assessment_detail",
        cascade="all, delete-orphan",
    )


class AssessmentImage(Base):
    __tablename__ = "assessment_images"
    __table_args__ = {"extend_existing": True}

    image_id = Column(Integer, primary_key=True, index=True)
    location_set_assessment_id = Column(
        Integer,
        ForeignKey("location_set_assessments.assessment_id"),
        nullable=False,
    )
    assessment_detail_id = Column(
        Integer,
        ForeignKey("location_assessments.assessment_detail_id"),
        nullable=True,
    )
    image_url = Column(String(255), nullable=False)
    description = Column(Text)
    uploaded_by = Column(String, ForeignKey("users.user_id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    location_set_assessment = relationship(
        "LocationSetAssessment", back_populates="assessment_images"
    )
    assessment_detail = relationship(
        "LocationAssessment", back_populates="assessment_images"
    )
    uploader = relationship("User")


class AssessmentComment(Base):
    __tablename__ = "assessment_comments"
    __table_args__ = {"extend_existing": True}

    comment_id = Column(Integer, primary_key=True, index=True)
    location_set_assessment_id = Column(
        Integer,
        ForeignKey("location_set_assessments.assessment_id"),
        nullable=False,
    )
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    comment_text = Column(Text, nullable=False)
    is_edited = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    location_set_assessment = relationship(
        "LocationSetAssessment", back_populates="assessment_comments"
    )
    user = relationship("User")
