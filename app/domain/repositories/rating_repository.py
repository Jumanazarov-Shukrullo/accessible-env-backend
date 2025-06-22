from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.rating_model import LocationRating


class RatingRepository(SQLAlchemyRepository[LocationRating, int]):
    def __init__(self, db: Session):
        super().__init__(LocationRating, db)

    def get_user_rating_for_location(
        self, user_id: UUID, location_id: UUID
    ) -> Optional[LocationRating]:
        """Get a user's rating for a specific location."""
        stmt = select(LocationRating).where(
            LocationRating.user_id == str(user_id),
            LocationRating.location_id == str(location_id),
        )
        return self.db.scalar(stmt)

    def get_ratings_for_location(
        self, location_id: UUID, limit: int = 50
    ) -> List[LocationRating]:
        """Get all ratings for a location, ordered by most recent."""
        stmt = (
            select(LocationRating)
            .where(LocationRating.location_id == str(location_id))
            .order_by(desc(LocationRating.created_at))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_average_rating_for_location(self, location_id: UUID) -> float:
        """Calculate the average rating for a location."""
        stmt = select(func.avg(LocationRating.rating)).where(
            LocationRating.location_id == str(location_id)
        )
        result = self.db.scalar(stmt)
        return float(result) if result else 0.0

    def get_rating_count_for_location(self, location_id: UUID) -> int:
        """Get the total number of ratings for a location."""
        stmt = select(func.count(LocationRating.rating_id)).where(
            LocationRating.location_id == str(location_id)
        )
        return self.db.scalar(stmt) or 0

    def get_ratings_by_user(
        self, user_id: UUID, limit: int = 50
    ) -> List[LocationRating]:
        """Get all ratings made by a user."""
        stmt = (
            select(LocationRating)
            .where(LocationRating.user_id == str(user_id))
            .order_by(desc(LocationRating.created_at))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
