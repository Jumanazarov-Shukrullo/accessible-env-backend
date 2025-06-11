from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.assessment_model import LocationAssessment


class AssessmentDetailRepository(SQLAlchemyRepository[LocationAssessment, int]):
    def __init__(self, db: Session):
        super().__init__(LocationAssessment, db)

    def list_for_header(self, header_id: int):
        return (
            self.db.query(LocationAssessment).filter(LocationAssessment.location_set_assessment_id == header_id).all()
        )
