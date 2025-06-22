from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.assessment_model import AccessibilityCriteria


class CriteriaRepository(SQLAlchemyRepository[AccessibilityCriteria, int]):
    def __init__(self, db: Session):
        super().__init__(AccessibilityCriteria, db)
