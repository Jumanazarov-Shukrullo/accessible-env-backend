from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.assessment_model import (
    AccessibilityCriteria,
    AssessmentSet,
    SetCriteria,
)


class AssessmentSetRepository(SQLAlchemyRepository[AssessmentSet, int]):
    def __init__(self, db: Session):
        super().__init__(AssessmentSet, db)

    def active(self):
        return self.db.scalars(
            select(AssessmentSet).where(AssessmentSet.is_active)
        ).all()

    def get_criteria(self, set_id: int):
        # Query criteria through the junction table
        criteria = (
            self.db.query(AccessibilityCriteria)
            .join(
                SetCriteria,
                SetCriteria.criterion_id == AccessibilityCriteria.criterion_id,
            )
            .filter(SetCriteria.set_id == set_id)
            .order_by(SetCriteria.sequence)
            .all()
        )
        return criteria
