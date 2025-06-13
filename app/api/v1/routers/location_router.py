from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, Response
from fastapi.exceptions import HTTPException

from app.api.v1.dependencies import get_uow, require_roles
from app.core.auth import auth_manager
from app.core.constants import RoleID
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.location_schema import LocationCreate, LocationFilter, LocationResponse, LocationUpdate, PaginatedLocations
from app.services.location_service import LocationService
from app.services.assessment_service import AssessmentService
from app.utils.logger import get_logger
from app.utils.pdf_report import render_pdf

logger = get_logger("location_router")


class LocationRouter:
    """Class wrapper around APIRouter to keep things OO."""

    def __init__(self) -> None:
        self.router = APIRouter(prefix="/locations", tags=["Locations"])
        self._register_routes()

    # ---------------------------------------------------------------------- #
    # private
    # ---------------------------------------------------------------------- #
    def _register_routes(self) -> None:
        # CRUD endpoints
        self.router.post(
            "/",
            response_model=LocationResponse,
            status_code=status.HTTP_201_CREATED,
            dependencies=[Depends(require_roles([RoleID.SUPERADMIN.value, RoleID.ADMIN.value]))],
        )(self._create_location)

        self.router.get("/", response_model=PaginatedLocations)(self._list_locations)
        
        # Public endpoints - Put these BEFORE the parameterized routes to avoid conflicts
        self.router.get("/popular", response_model=List[LocationResponse])(self._get_popular_locations)
        self.router.get("/recently-rated", response_model=List[LocationResponse])(self._get_recently_rated_locations)
        
        self.router.get("/{location_id}", response_model=LocationResponse)(self._get_location)
        self.router.get("/{location_id}/images")(self._get_location_images)

        self.router.put(
            "/{location_id}",
            response_model=LocationResponse,
            dependencies=[Depends(require_roles([RoleID.SUPERADMIN.value, RoleID.ADMIN.value]))],
        )(self._update_location)

        # Filter endpoints
        self.router.get("/by_category/{category_id}", response_model=List[LocationResponse])(self._get_by_category)
        self.router.get("/by_region/{region_id}", response_model=List[LocationResponse])(self._get_by_region)
        self.router.get("/by_district/{district_id}", response_model=List[LocationResponse])(self._get_by_district)
        self.router.get("/by_city/{city_id}", response_model=List[LocationResponse])(self._get_by_city)

        # Inspector management
        self.router.post(
            "/{location_id}/inspectors/{user_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            dependencies=[Depends(require_roles([RoleID.SUPERADMIN.value]))],
        )(self._assign_inspector)

        self.router.delete(
            "/{location_id}/inspectors/{user_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            dependencies=[Depends(require_roles([RoleID.SUPERADMIN.value]))],
        )(self._remove_inspector)

        # Location interaction endpoints
        self.router.get("/{location_id}/stats", response_model=dict)(self._get_location_stats)
        self.router.get("/{location_id}/favorites/status")(self._get_favorite_status)
        self.router.post("/{location_id}/favorites", status_code=status.HTTP_201_CREATED)(self._add_to_favorites)
        self.router.delete("/{location_id}/favorites", status_code=status.HTTP_204_NO_CONTENT)(self._remove_from_favorites)
        self.router.get("/{location_id}/ratings")(self._get_location_ratings)
        self.router.post("/{location_id}/ratings", status_code=status.HTTP_201_CREATED)(self._add_rating)

        # PDF report
        self.router.get("/{location_id}/report", response_class=Response)(self._download_report)

    # ---------------------------------------------------------------------- #
    # endpoints
    # ---------------------------------------------------------------------- #
    async def _create_location(
        self,
        payload: LocationCreate,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Creating location")
        return LocationService(uow).create_location(payload, current_user)

    async def _get_location(
        self,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Getting location {location_id}")
        return LocationService(uow).get_location_detail(str(location_id))

    async def _get_location_images(
        self,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Getting images for location {location_id}")
        location = LocationService(uow).get_location_detail(str(location_id))
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        return location.images or []

    async def _update_location(
        self,
        location_id: UUID,
        payload: LocationUpdate,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Updating location {location_id}")
        return LocationService(uow).update_location(location_id, payload, current_user)

    async def _list_locations(
        self,
        category_id: Optional[int] = None,
        region_id: Optional[int] = None,
        district_id: Optional[int] = None,
        city_id: Optional[int] = None,
        status: Optional[str] = None,
        min_score: Optional[float] = None,
        search: Optional[str] = None,
        page: int = Query(default=1, ge=1),
        size: int = Query(default=50, ge=1, le=100),
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Listing locations with filters")
        filters = LocationFilter(
            category_id=category_id,
            region_id=region_id,
            district_id=district_id,
            city_id=city_id,
            status=status,
            min_accessibility_score=min_score,
        )
        return LocationService(uow).get_locations_paginated(page=page, size=size, filters=filters)

    async def _get_by_category(
        self,
        category_id: int,
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info(f"Getting locations by category {category_id}")
        return LocationService(uow).get_locations_by_category(category_id)

    async def _get_by_region(
        self,
        region_id: int,
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info(f"Getting locations by region {region_id}")
        return LocationService(uow).get_locations_by_region(region_id)

    async def _get_by_district(
        self,
        district_id: int,
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info(f"Getting locations by district {district_id}")
        return LocationService(uow).get_locations_by_district(district_id)

    async def _get_by_city(
        self,
        city_id: int,
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info(f"Getting locations by city {city_id}")
        return LocationService(uow).get_locations_by_city(city_id)

    async def _get_popular_locations(
        self,
        limit: int = Query(default=10, ge=1, le=100),
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info(f"Getting popular locations with limit {limit}")
        return LocationService(uow).get_popular_locations(limit)

    async def _get_recently_rated_locations(
        self,
        limit: int = Query(default=10, ge=1, le=100),
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info(f"Getting recently rated locations with limit {limit}")
        return LocationService(uow).get_recently_rated_locations(limit)

    async def _assign_inspector(
        self,
        location_id: UUID,
        user_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Assigning inspector {user_id} to location {location_id}")
        LocationService(uow).assign_inspector(current_user, location_id, user_id)

    async def _remove_inspector(
        self,
        location_id: UUID,
        user_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Removing inspector {user_id} from location {location_id}")
        LocationService(uow).unassign_inspector(current_user, location_id, user_id)

    async def _get_location_stats(
        self,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info(f"Getting location stats for {location_id}")
        return LocationService(uow).get_location_stats(location_id)

    async def _get_favorite_status(
        self,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info(f"Getting favorite status for location {location_id}")
        return LocationService(uow).get_favorite_status(location_id)

    async def _add_to_favorites(
        self,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info(f"Adding location {location_id} to favorites")
        LocationService(uow).add_to_favorites(location_id)

    async def _remove_from_favorites(
        self,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info(f"Removing location {location_id} from favorites")
        LocationService(uow).remove_from_favorites(location_id)

    async def _get_location_ratings(
        self,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info(f"Getting ratings for location {location_id}")
        return LocationService(uow).get_location_ratings(location_id)

    async def _add_rating(
        self,
        location_id: UUID,
        rating: float,
        uow: UnitOfWork = Depends(get_uow),
    ):
        logger.info(f"Adding rating {rating} to location {location_id}")
        LocationService(uow).add_rating(location_id, rating)

    async def _download_report(
        self,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        # Anyone with access can download
        loc_service = LocationService(uow)
        location = loc_service.get_location_detail(location_id)
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")

        # Images
        images = location.images

        # Get verified assessments for report
        assess_service = AssessmentService(uow)
        verified_details: list = []
        assessments = assess_service.list_location_assessments(location_id)
        for a in assessments:
            if a.is_verified:
                verified_details.extend(assess_service.get_assessment_details(a.assessment_id))

        pdf_bytes = render_pdf(
            "report.html",
            {
                "location": location,
                "images": images,
                "assessments": verified_details,
            },
        )
        headers = {"Content-Disposition": f"attachment; filename=location_{location_id}.pdf"}
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


# -------- expose -----------------------------------------------------------
location_router = LocationRouter().router
