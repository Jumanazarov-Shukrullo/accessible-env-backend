from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import auth_manager
from app.models.user_model import User
from app.schemas.rating_schema import RatingCreate, RatingOut, LocationRatingStats
from app.services.rating_service import RatingService
from app.utils.logger import get_logger
from app.api.v1.dependencies import get_uow
from app.domain.unit_of_work import UnitOfWork

logger = get_logger("rating_router")


class RatingRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/ratings", tags=["Ratings"])
        self.register_routes()

    def register_routes(self):
        # User rating operations
        self.router.add_api_route(
            "/location/{location_id}",
            self.add_rating,
            methods=["POST"],
            response_model=RatingOut
        )
        self.router.add_api_route(
            "/location/{location_id}/my-rating",
            self.get_my_rating,
            methods=["GET"],
            response_model=Optional[RatingOut]
        )
        self.router.add_api_route(
            "/location/{location_id}/my-rating",
            self.delete_my_rating,
            methods=["DELETE"],
            status_code=204
        )
        
        # Location rating information
        self.router.add_api_route(
            "/location/{location_id}/all",
            self.get_location_ratings,
            methods=["GET"],
            response_model=List[RatingOut]
        )
        self.router.add_api_route(
            "/location/{location_id}/stats",
            self.get_location_stats,
            methods=["GET"],
            response_model=LocationRatingStats
        )

    async def add_rating(
        self,
        location_id: UUID,
        payload: RatingCreate,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user)
    ) -> RatingOut:
        """Add or update a rating for a location."""
        logger.info(f"Adding rating for location {location_id} by user {current_user.user_id}")
        
        # Override location_id from URL
        payload.location_id = location_id
        
        service = RatingService(uow)
        return service.add_rating(payload, current_user)

    async def get_my_rating(
        self,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user)
    ) -> Optional[RatingOut]:
        """Get the current user's rating for a location."""
        logger.info(f"Getting user rating for location {location_id} by user {current_user.user_id}")
        
        service = RatingService(uow)
        return service.get_user_rating(location_id, current_user)

    async def delete_my_rating(
        self,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user)
    ):
        """Delete the current user's rating for a location."""
        logger.info(f"Deleting user rating for location {location_id} by user {current_user.user_id}")
        
        service = RatingService(uow)
        service.delete_rating(location_id, current_user)

    async def get_location_ratings(
        self,
        location_id: UUID,
        limit: int = Query(50, le=100),
        uow: UnitOfWork = Depends(get_uow)
    ) -> List[RatingOut]:
        """Get all ratings for a location."""
        logger.info(f"Getting all ratings for location {location_id}")
        
        service = RatingService(uow)
        return service.get_location_ratings(location_id, limit)

    async def get_location_stats(
        self,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow)
    ) -> LocationRatingStats:
        """Get rating statistics for a location."""
        logger.info(f"Getting rating stats for location {location_id}")
        
        service = RatingService(uow)
        return service.get_location_rating_stats(location_id)


rating_router = RatingRouter().router 