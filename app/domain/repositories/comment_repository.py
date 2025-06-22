from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.comment_model import Comment


class CommentRepository(SQLAlchemyRepository[Comment, int]):
    def __init__(self, db: Session):
        super().__init__(Comment, db)

    def thread(self):
        """Return top‑level comments with joined children."""
        return (
            self.db.query(Comment)
            .filter(Comment.parent_comment_id.is_(None))
            .order_by(Comment.created_at.desc())
            .all()
        )
