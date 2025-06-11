from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.v1.dependencies import get_uow
from app.core.auth import auth_manager
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.rating_schema import RatingCreate, RatingOut
from app.schemas.review_schema import ReviewSchema
from app.services.review_service import ReviewService
from app.utils.logger import get_logger

logger = get_logger("review_router")


class ReviewRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/reviews", tags=["Reviews & Ratings"])
        self._register()

    def _register(self):
        self.router.post("/", response_model=ReviewSchema.Out, status_code=201)(self._create_review)
        self.router.put("/{review_id}", response_model=ReviewSchema.Out)(self._update_review)
        self.router.delete("/{review_id}", status_code=204)(self._delete_review)
        self.router.get("/location/{location_id}", response_model=list[ReviewSchema.Out])(self._list_reviews)

        # Ratings
        self.router.post("/ratings", response_model=RatingOut, status_code=201)(self._rate_location)

    # ---------------- endpoints --------------------------------------
    async def _create_review(
        self,
        payload: ReviewSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Creating a new review")
        return ReviewService(uow).create_review(payload, current)

    async def _update_review(
        self,
        review_id: int,
        payload: ReviewSchema.Update,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Updating a review")
        return ReviewService(uow).update_review(review_id, payload, current)

    async def _delete_review(
        self, review_id: int, uow: UnitOfWork = Depends(get_uow), current: User = Depends(auth_manager.get_current_user)
    ):
        logger.info("Deleting a review")
        ReviewService(uow).delete_review(review_id, current)

    async def _list_reviews(self, location_id: UUID, uow: UnitOfWork = Depends(get_uow)):
        logger.info("Listing reviews for a location")
        return ReviewService(uow).list_by_location(location_id)

    # --- ratings -----------------------------------------------------
    async def _rate_location(
        self,
        payload: RatingCreate,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Rating a location")
        return ReviewService(uow).rate_location(payload, current)


review_router = ReviewRouter().router
