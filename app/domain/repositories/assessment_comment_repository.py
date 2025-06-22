from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.assessment_model import AssessmentComment


class AssessmentCommentRepository(
    SQLAlchemyRepository[AssessmentComment, int]
):
    def __init__(self, db: Session):
        super().__init__(AssessmentComment, db)
