from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from app.domain.unit_of_work import UnitOfWork
from app.models.rating_model import LocationRating
from app.models.user_model import User
from app.schemas.rating_schema import (
    LocationRatingStats,
    RatingCreate,
    RatingOut,
)
from app.utils.logger import get_logger


logger = get_logger("rating_service")


class RatingService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def add_rating(self, data: RatingCreate, current_user: User) -> RatingOut:
        """Add or update a user's rating for a location."""
        with self.uow:
            # Check if user already rated this location
            existing_rating = self.uow.ratings.get_user_rating_for_location(
                current_user.user_id, data.location_id
            )

            if existing_rating:
                # Update existing rating
                existing_rating.rating = data.rating
                if data.comment is not None:
                    existing_rating.comment = data.comment
                self.uow.commit()
                logger.info(
                    f"Updated rating for location {
                        data.location_id} by user {
                        current_user.user_id}")
                return self._format_rating_output(existing_rating)
            else:
                # Create new rating
                new_rating = LocationRating(
                    location_id=str(data.location_id),
                    user_id=str(current_user.user_id),
                    rating=data.rating,
                    comment=data.comment,
                )
                self.uow.ratings.add(new_rating)
                self.uow.commit()
                logger.info(
                    f"Added new rating for location {
                        data.location_id} by user {
                        current_user.user_id}")
                return self._format_rating_output(new_rating)

    def get_user_rating(
        self, location_id: UUID, current_user: User
    ) -> Optional[RatingOut]:
        """Get the current user's rating for a location."""
        rating = self.uow.ratings.get_user_rating_for_location(
            current_user.user_id, location_id
        )
        if not rating:
            return None
        return self._format_rating_output(rating)

    def get_location_ratings(
        self, location_id: UUID, limit: int = 50
    ) -> List[RatingOut]:
        """Get all ratings for a location."""
        ratings = self.uow.ratings.get_ratings_for_location(location_id, limit)
        return [self._format_rating_output(rating) for rating in ratings]

    def get_location_rating_stats(
        self, location_id: UUID
    ) -> LocationRatingStats:
        """Get rating statistics for a location."""
        average_rating = self.uow.ratings.get_average_rating_for_location(
            location_id
        )
        total_ratings = self.uow.ratings.get_rating_count_for_location(
            location_id
        )

        # Get rating distribution
        ratings = self.uow.ratings.get_ratings_for_location(
            location_id, limit=1000
        )
        distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

        for rating in ratings:
            rounded_rating = str(int(round(rating.rating)))
            if rounded_rating in distribution:
                distribution[rounded_rating] += 1

        return LocationRatingStats(
            location_id=location_id,
            average_rating=round(average_rating, 2),
            total_ratings=total_ratings,
            rating_distribution=distribution,
        )

    def delete_rating(self, location_id: UUID, current_user: User) -> bool:
        """Delete a user's rating for a location."""
        with self.uow:
            rating = self.uow.ratings.get_user_rating_for_location(
                current_user.user_id, location_id
            )
            if not rating:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Rating not found",
                )

            self.uow.ratings.delete(rating)
            self.uow.commit()
            logger.info(
                f"Deleted rating for location {location_id} by user {
                    current_user.user_id}")
            return True

    def _format_rating_output(self, rating: LocationRating) -> RatingOut:
        """Format a rating for output, including user information."""
        # Get user info if available
        user_name = None
        user_full_name = None

        if hasattr(rating, "user") and rating.user:
            user_name = rating.user.username
            # Access profile data from normalized structure
            if rating.user.profile:
                profile = rating.user.profile
                middle = (
                    f" {profile.middle_name}" if profile.middle_name else ""
                )
                user_full_name = (
                    f"{profile.first_name}{middle} {profile.surname}".strip()
                )

        return RatingOut(
            rating_id=rating.rating_id,
            location_id=UUID(rating.location_id),
            user_id=UUID(rating.user_id),
            rating=rating.rating,
            comment=rating.comment,
            created_at=rating.created_at,
            updated_at=rating.updated_at,
            user_name=user_name,
            user_full_name=user_full_name,
        )
