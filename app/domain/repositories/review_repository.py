from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.review_model import Review


class ReviewRepository(SQLAlchemyRepository[Review, int]):
    def __init__(self, db: Session):
        super().__init__(Review, db)

    def for_location(self, loc_id: UUID):
        stmt = select(Review).where(
            Review.location_id == str(loc_id), Review.is_approved is True
        )
        return self.db.scalars(stmt).all()

    def by_user(self, user_id: UUID):
        return self.db.scalars(
            select(Review).where(Review.user_id == str(user_id))
        ).all()
