from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.assessment_model import SetCriteria


class SetCriteriaRepository(SQLAlchemyRepository[SetCriteria, tuple[int, int]]):
    def __init__(self, db: Session):
        super().__init__(SetCriteria, db)

    def list_for_set(self, set_id: int):
        return self.db.query(SetCriteria).filter(SetCriteria.set_id == set_id).order_by(SetCriteria.sequence).all()
