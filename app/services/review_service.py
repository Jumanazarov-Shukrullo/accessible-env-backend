from uuid import UUID

from fastapi import HTTPException

from app.domain.unit_of_work import UnitOfWork
from app.models.rating_model import LocationRating
from app.models.review_model import Review
from app.models.user_model import User
from app.schemas.rating_schema import RatingCreate
from app.schemas.review_schema import ReviewSchema


class ReviewService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # ---------------- Reviews ----------------------------------------
    def create_review(
        self, payload: ReviewSchema.Create, user: User
    ) -> Review:
        with self.uow:
            review = Review(**payload.dict(), user_id=str(user.user_id))
            self.uow.reviews.add(review)
            self.uow.commit()
            return review

    def update_review(
        self, review_id: int, payload: ReviewSchema.Update, user: User
    ) -> Review:
        review = self._get_review_owned(review_id, user)
        for field, val in payload.dict(exclude_unset=True).items():
            setattr(review, field, val)
        self.uow.commit()
        return review

    def delete_review(self, review_id: int, user: User):
        review = self._get_review_owned(review_id, user)
        self.uow.reviews.delete(review)
        self.uow.commit()

    def list_by_location(self, loc_id: UUID):
        return self.uow.reviews.for_location(loc_id)

    # ---------------- Ratings ----------------------------------------
    def rate_location(
        self, payload: RatingCreate, user: User
    ) -> LocationRating:
        if not 1.0 <= payload.rating <= 5.0:
            raise HTTPException(400, "Rating must be 1.0-5.0")

        with self.uow:
            # Check if user already rated this location
            existing = self.uow.ratings.get_user_rating_for_location(
                user.user_id, payload.location_id
            )
            if existing:
                # Update existing rating
                existing.rating = payload.rating
                existing.comment = payload.comment
                self.uow.commit()
                return existing

            # Create new rating
            rating = LocationRating(
                location_id=str(payload.location_id),
                user_id=str(user.user_id),
                rating=payload.rating,
                comment=payload.comment,
            )
            self.uow.ratings.add(rating)
            self.uow.commit()
            return rating

    # ---------------- helpers ----------------------------------------
    def _get_review_owned(self, review_id: int, user: User) -> Review:
        review = self.uow.reviews.get(review_id)
        if not review:
            raise HTTPException(404, "Review not found")
        if review.user_id != str(user.user_id):
            raise HTTPException(403, "Not owner")
        return review
