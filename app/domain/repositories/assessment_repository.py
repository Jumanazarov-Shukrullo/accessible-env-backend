# app/repositories/assessment_repository.py
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.assessment_model import AssessmentStatus, LocationSetAssessment


class AssessmentRepository(SQLAlchemyRepository[LocationSetAssessment, int]):
    def __init__(self, db: Session):
        super().__init__(LocationSetAssessment, db)

    # custom ------------------------------------------------------------
    def by_location(self, loc_id: str) -> Sequence[LocationSetAssessment]:
        stmt = select(LocationSetAssessment).where(
            LocationSetAssessment.location_id == loc_id
        )
        return self.db.execute(stmt).scalars().all()

    def by_assessor(self, assessor_id: str):
        stmt = select(LocationSetAssessment).where(
            LocationSetAssessment.assessor_id == assessor_id
        )
        return self.db.execute(stmt).scalars().all()

    def verify(self, assessment: LocationSetAssessment, verifier_id: str):
        assessment.status = AssessmentStatus.verified
        assessment.verifier_id = verifier_id
        self.update(assessment)
        self.db.commit()

    def list_by_location(
        self, location_id: str
    ) -> list[LocationSetAssessment]:
        """Get all assessments for a location"""
        # Updated to use proper ID type handling
        return (
            self.db.query(LocationSetAssessment)
            .filter(LocationSetAssessment.location_id == location_id)
            .all()
        )
