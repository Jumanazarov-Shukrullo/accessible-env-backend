from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.domain.unit_of_work import UnitOfWork
from app.models.category_model import Category
from app.models.city_model import City
from app.models.district_model import District
from app.models.favourite_model import Favourite
from app.models.location_inspector_model import LocationInspector
from app.models.location_model import Location, LocationDetails, LocationStats
from app.models.rating_model import LocationRating
from app.models.region_model import Region
from app.models.user_model import User
from app.schemas.location_schema import (
    LocationCreate,
    LocationDetailResponse,
    LocationFilter,
    LocationListResponse,
    LocationResponse,
    LocationSearch,
    LocationSearchResponse,
    LocationUpdate,
    PaginatedLocations,
)
from app.utils.cache import cache
from app.utils.logger import get_logger


logger = get_logger("location_service")


class LocationService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def _patch_image_urls(self, images):
        """
        Converts image object names (keys) to fully qualified URLs using Minio settings.
        This method might be deprecated if frontend constructs URLs via API proxy.
        """
        patched_images = []
        # Ensure settings are loaded if this method is to be used
        # from app.core.config import settings
        # base_url = f"http://{settings.storage.minio_endpoint}/{settings.storage.minio_bucket}"

        # Fallback or placeholder if direct URL construction is problematic or not desired for public exposure
        # For now, let's assume if this function is called, it's an internal path or object key desired.
        # Or, if the goal was to provide the API-proxied URL, that logic would
        # be different.

        for img in images:
            # If img.image_url is already a full URL from another source, or if it's an object key,
            # this logic needs to be clear.
            # Assuming img.image_url from DB is an object key:
            # patched_url = f"{base_url}/{img.image_url.lstrip('/')}"

            # If the goal is to return the object key itself for the frontend
            # to handle:
            patched_url = img.image_url

            patched_images.append(
                {
                    "image_id": img.image_id,
                    # Sending object key
                    "image_url": f"{settings.storage.minio_endpoint}/{settings.storage.minio_bucket}/{patched_url}",
                    "description": img.description,
                    "position": img.position,
                }
            )
        return patched_images

    # ---------------- CRUD -------------------------------------------
    def ensure_uuid(self, val):
        return val if isinstance(val, UUID) else UUID(val)

    def create_location(
        self, location_in: LocationCreate, created_by: User
    ) -> LocationResponse:
        """Create location with details and stats tables"""
        with self.uow:
            # Create core location record
            location = Location(
                location_name=location_in.location_name,
                address=location_in.address,
                latitude=location_in.latitude,
                longitude=location_in.longitude,
                category_id=location_in.category_id,
                region_id=location_in.region_id,
                district_id=location_in.district_id,
                city_id=location_in.city_id,
                status=location_in.status,
            )
            self.uow.db.add(location)
            self.uow.db.flush()  # Get location_id

            # Create location details
            details = LocationDetails(
                location_id=location.location_id,
                contact_info=location_in.contact_info,
                website_url=location_in.website_url,
                operating_hours=location_in.operating_hours,
                description=location_in.description,
            )
            self.uow.db.add(details)

            # Create location stats
            stats = LocationStats(
                location_id=location.location_id,
                total_reviews=0,
                total_ratings=0,
            )
            self.uow.db.add(stats)

            self.uow.commit()

            logger.info(
                f"Location {
                    location.location_name} created by {
                    created_by.username}")
            return self.get_location_with_details(location.location_id)

    @cache.cacheable(
        lambda self, location_id: f"location_details:{location_id}", ttl=300
    )  # 5 minutes cache
    def get_location_with_details(
        self, location_id: str
    ) -> Optional[LocationResponse]:
        """Get location with all related data"""
        location = (
            self.uow.db.query(Location)
            .options(
                joinedload(Location.details),
                joinedload(Location.stats),
                joinedload(Location.images),
                joinedload(Location.category),
                joinedload(Location.region),
                joinedload(Location.district),
                joinedload(Location.city),
                joinedload(Location.inspectors).joinedload(
                    LocationInspector.user
                ),
            )
            .filter(Location.location_id == location_id)
            .first()
        )

        if not location:
            return None

        # Build breadcrumb navigation
        breadcrumb = []
        try:
            # First, add the base (root) category
            if location.category:
                # Find the root category by traversing up the tree
                current_cat = location.category
                category_hierarchy = [current_cat]

                # Build the full category hierarchy from current to root
                while current_cat and current_cat.parent_category_id:
                    parent_cat = (
                        self.uow.db.query(Category)
                        .filter(
                            Category.category_id
                            == current_cat.parent_category_id
                        )
                        .first()
                    )
                    if parent_cat:
                        category_hierarchy.insert(0, parent_cat)
                        current_cat = parent_cat
                    else:
                        break

                # Add only the root (base) category first
                root_category = category_hierarchy[0]
                breadcrumb.append(
                    {
                        "type": "category",
                        "id": root_category.category_id,
                        "name": root_category.category_name,
                        "slug": root_category.slug,
                    }
                )

            # Second, add geographical hierarchy: region → district → city
            if location.region:
                breadcrumb.append(
                    {
                        "type": "region",
                        "id": location.region.region_id,
                        "name": location.region.region_name,
                    }
                )

            if location.district:
                breadcrumb.append(
                    {
                        "type": "district",
                        "id": location.district.district_id,
                        "name": location.district.district_name,
                    }
                )

            if location.city:
                breadcrumb.append(
                    {
                        "type": "city",
                        "id": location.city.city_id,
                        "name": location.city.city_name,
                    }
                )

            # Finally, add child categories AFTER geographical data (if current
            # category is not root)
            if location.category and location.category.parent_category_id:
                # Get the category hierarchy we built earlier
                current_cat = location.category
                category_hierarchy = [current_cat]

                # Rebuild category hierarchy for child categories
                while current_cat and current_cat.parent_category_id:
                    parent_cat = (
                        self.uow.db.query(Category)
                        .filter(
                            Category.category_id
                            == current_cat.parent_category_id
                        )
                        .first()
                    )
                    if parent_cat:
                        category_hierarchy.insert(0, parent_cat)
                        current_cat = parent_cat
                    else:
                        break

                # Add intermediate categories (skip root, add children after
                # geographical data)
                for i, cat in enumerate(category_hierarchy):
                    if i > 0:  # Skip root category (already added)
                        breadcrumb.append(
                            {
                                "type": "category",
                                "id": cat.category_id,
                                "name": cat.category_name,
                                "slug": cat.slug,
                            }
                        )

        except Exception as e:
            logger.warning(
                f"Error building breadcrumb for location {location_id}: {e}"
            )
            breadcrumb = []

        # Finally add the location itself
        breadcrumb.append(
            {
                "type": "location",
                "id": str(location.location_id),
                "name": location.location_name,
            }
        )

        # Create response manually to ensure all nested data is included with
        # proper string conversion
        response_data = {
            "location_id": str(location.location_id),
            "location_name": location.location_name,
            "address": location.address,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "category_id": location.category_id,
            "region_id": location.region_id,
            "district_id": location.district_id,
            "city_id": location.city_id,
            "status": location.status,
            "created_at": location.created_at,
            "updated_at": location.updated_at,
            "details": None,
            "stats": None,
            "images": [],
            "inspectors": [],
            "breadcrumb": breadcrumb,
            # Add category and region names for proper display
            "category_name": (
                location.category.category_name if location.category else None
            ),
            "region_name": (
                location.region.region_name if location.region else None
            ),
            "district_name": (
                location.district.district_name if location.district else None
            ),
            "city_name": location.city.city_name if location.city else None,
            "primary_image_url": None,  # Will be set below if images exist
        }

        # Add details if present with proper string conversion
        if location.details:
            response_data["details"] = {
                "location_id": str(location.details.location_id),
                "contact_info": location.details.contact_info,
                "website_url": location.details.website_url,
                "operating_hours": location.details.operating_hours,
                "description": location.details.description,
                "created_at": location.details.created_at,
                "updated_at": location.details.updated_at,
            }

        # Add stats if present with proper string conversion
        if location.stats:
            response_data["stats"] = {
                "location_id": str(location.stats.location_id),
                "accessibility_score": location.stats.accessibility_score,
                "total_reviews": location.stats.total_reviews,
                "total_ratings": location.stats.total_ratings,
                "average_rating": location.stats.average_rating,
                "last_assessment_date": location.stats.last_assessment_date,
                "updated_at": location.stats.updated_at,
            }

        # Add images if present with proper string conversion and full URLs
        if location.images:
            for image in location.images:
                # Construct full MinIO URL
                full_image_url = f"http://{
                    settings.storage.minio_endpoint}/{
                    settings.storage.minio_bucket}/{
                    image.image_url}"
                response_data["images"].append(
                    {
                        "image_id": image.image_id,
                        "location_id": str(image.location_id),
                        "image_url": full_image_url,
                        "description": image.description,
                        "position": image.position,
                        "created_at": image.created_at,
                    }
                )

        # Add inspectors if present with proper user and profile data
        if location.inspectors:
            for inspector in location.inspectors:
                inspector_data = {
                    "user_id": str(inspector.user_id),
                    "location_id": str(inspector.location_id),
                    "assigned_at": inspector.assigned_at,
                    "username": None,
                    "first_name": None,
                    "surname": None,
                    "middle_name": None,
                    "email": None,
                }

                # Add user details if available
                if inspector.user:
                    inspector_data["username"] = inspector.user.username
                    inspector_data["email"] = inspector.user.email

                    # Add profile details if available
                    if inspector.user.profile:
                        inspector_data["first_name"] = (
                            inspector.user.profile.first_name
                        )
                        inspector_data["surname"] = (
                            inspector.user.profile.surname
                        )
                        inspector_data["middle_name"] = (
                            inspector.user.profile.middle_name
                        )

                # Add full_name for compatibility
                if inspector_data["first_name"] or inspector_data["surname"]:
                    full_name_parts = []
                    if inspector_data["first_name"]:
                        full_name_parts.append(inspector_data["first_name"])
                    if inspector_data["surname"]:
                        full_name_parts.append(inspector_data["surname"])
                    inspector_data["full_name"] = " ".join(full_name_parts)
                else:
                    inspector_data["full_name"] = inspector_data["username"]

                response_data["inspectors"].append(inspector_data)

        # Set primary_image_url if images exist
        if location.images and len(location.images) > 0:
            response_data["primary_image_url"] = (
                f"http://{settings.storage.minio_endpoint}/{settings.storage.minio_bucket}/{location.images[0].image_url}"
            )

        return LocationResponse(**response_data)

    @cache.cacheable(
        lambda self, location_id: f"location:detail:{location_id}", ttl=300
    )
    def get_location_detail(
        self, location_id: str
    ) -> Optional[LocationDetailResponse]:
        """Get location with detailed information for display"""
        with self.uow:
            loc = self.uow.locations.get_full(location_id)
            if not loc:
                return None

            # Convert the location object to dict first and ensure UUIDs are
            # strings
            loc_dict = {
                "location_id": str(loc.location_id),
                "location_name": loc.location_name,
                "address": loc.address,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "category_id": loc.category_id,
                "region_id": loc.region_id,
                "district_id": loc.district_id,
                "city_id": loc.city_id,
                "status": loc.status,
                "created_at": (
                    loc.created_at.isoformat() if loc.created_at else None
                ),
                "updated_at": (
                    loc.updated_at.isoformat() if loc.updated_at else None
                ),
                "details": (
                    {
                        "location_id": str(loc.location_id),
                        "contact_info": (
                            loc.details.contact_info
                            if loc.details
                            and hasattr(loc.details, "contact_info")
                            else None
                        ),
                        "website_url": (
                            loc.details.website_url
                            if loc.details
                            and hasattr(loc.details, "website_url")
                            else None
                        ),
                        "description": (
                            loc.details.description
                            if loc.details
                            and hasattr(loc.details, "description")
                            else None
                        ),
                        "operating_hours": (
                            loc.details.operating_hours
                            if loc.details
                            and hasattr(loc.details, "operating_hours")
                            else None
                        ),
                        "created_at": (
                            loc.details.created_at.isoformat()
                            if loc.details and loc.details.created_at
                            else None
                        ),
                        "updated_at": (
                            loc.details.updated_at.isoformat()
                            if loc.details and loc.details.updated_at
                            else None
                        ),
                    }
                    if loc.details
                    else None
                ),
                "stats": (
                    {
                        "location_id": str(loc.location_id),
                        "accessibility_score": (
                            loc.stats.accessibility_score
                            if loc.stats
                            else None
                        ),
                        "total_reviews": (
                            loc.stats.total_reviews if loc.stats else 0
                        ),
                        "average_rating": (
                            loc.stats.average_rating if loc.stats else None
                        ),
                        "total_ratings": (
                            loc.stats.total_ratings if loc.stats else 0
                        ),
                        "last_assessment_date": (
                            loc.stats.last_assessment_date.isoformat()
                            if loc.stats and loc.stats.last_assessment_date
                            else None
                        ),
                        "updated_at": (
                            loc.stats.updated_at.isoformat()
                            if loc.stats and loc.stats.updated_at
                            else None
                        ),
                    }
                    if loc.stats
                    else None
                ),
                "images": [
                    {
                        "image_id": str(img.image_id),
                        "image_url": f"http://{settings.storage.minio_endpoint}/{settings.storage.minio_bucket}/{img.image_url}",
                        "description": img.description,
                        "position": img.position,
                        "location_id": str(img.location_id),
                        "created_at": (
                            img.created_at.isoformat()
                            if img.created_at
                            else None
                        ),
                    }
                    for img in (loc.images or [])
                ],
                "inspectors": [
                    {
                        "user_id": str(insp.user_id),
                        "username": insp.username,
                        "first_name": insp.first_name,
                        "surname": insp.surname,
                        "email": insp.email,
                        "assigned_at": (
                            insp.assigned_at.isoformat()
                            if insp.assigned_at
                            else None
                        ),
                    }
                    for insp in (loc.inspectors or [])
                ],
            }

            # Add breadcrumb data - build proper breadcrumb trail
            # Order: Base Category → Region → District → City → Child Categories → Location
            breadcrumb = []

            # First, add the base (root) category only
            if loc.category_id:
                category = (
                    self.uow.db.query(Category)
                    .filter(Category.category_id == loc.category_id)
                    .first()
                )
                if category:
                    # Build the full category hierarchy from current to root
                    category_hierarchy = [category]
                    current_cat = category

                    while current_cat and current_cat.parent_category_id:
                        parent_cat = (
                            self.uow.db.query(Category)
                            .filter(
                                Category.category_id == current_cat.parent_category_id
                            )
                            .first()
                        )
                        if parent_cat:
                            category_hierarchy.insert(0, parent_cat)
                            current_cat = parent_cat
                        else:
                            break

                    # Add only the root (base) category first
                    root_category = category_hierarchy[0]
                    breadcrumb.append(
                        {
                            "type": "category",
                            "id": root_category.category_id,
                            "name": root_category.category_name,
                        }
                    )

            # Second, add geographical hierarchy: region → district → city
            if loc.region_id:
                region = (
                    self.uow.db.query(Region)
                    .filter(Region.region_id == loc.region_id)
                    .first()
                )
                if region:
                    breadcrumb.append(
                        {
                            "type": "region",
                            "id": region.region_id,
                            "name": region.region_name,
                        }
                    )
                    loc_dict["region_name"] = region.region_name

            if loc.district_id:
                district = (
                    self.uow.db.query(District)
                    .filter(District.district_id == loc.district_id)
                    .first()
                )
                if district:
                    breadcrumb.append(
                        {
                            "type": "district",
                            "id": district.district_id,
                            "name": district.district_name,
                        }
                    )
                    loc_dict["district_name"] = district.district_name

            if loc.city_id:
                city = (
                    self.uow.db.query(City)
                    .filter(City.city_id == loc.city_id)
                    .first()
                )
                if city:
                    breadcrumb.append(
                        {
                            "type": "city",
                            "id": city.city_id,
                            "name": city.city_name,
                        }
                    )
                    loc_dict["city_name"] = city.city_name

            # Finally, add child categories AFTER geographical data (if current category is not root)
            if loc.category_id:
                category = (
                    self.uow.db.query(Category)
                    .filter(Category.category_id == loc.category_id)
                    .first()
                )
                if category and category.parent_category_id:
                    # Rebuild category hierarchy for child categories
                    category_hierarchy = [category]
                    current_cat = category

                    while current_cat and current_cat.parent_category_id:
                        parent_cat = (
                            self.uow.db.query(Category)
                            .filter(
                                Category.category_id == current_cat.parent_category_id
                            )
                            .first()
                        )
                        if parent_cat:
                            category_hierarchy.insert(0, parent_cat)
                            current_cat = parent_cat
                        else:
                            break

                    # Add intermediate categories (skip root, add children after geographical data)
                    for i, cat in enumerate(category_hierarchy):
                        if i > 0:  # Skip root category (already added)
                            breadcrumb.append(
                                {
                                    "type": "category",
                                    "id": cat.category_id,
                                    "name": cat.category_name,
                                }
                            )

            # Finally add the location itself
            breadcrumb.append(
                {
                    "type": "location",
                    "id": str(loc.location_id),
                    "name": loc.location_name,
                }
            )

            loc_dict["breadcrumb"] = breadcrumb

            # Add category name to the main object
            if loc.category_id:
                category = (
                    self.uow.db.query(Category)
                    .filter(Category.category_id == loc.category_id)
                    .first()
                )
                if category:
                    loc_dict["category_name"] = category.category_name

            resp = LocationDetailResponse.model_validate(loc_dict)
            return resp

    def update_location(
        self,
        location_id: UUID,
        location_update: LocationUpdate,
        updated_by: User,
    ) -> LocationResponse:
        """Update location - enhanced to handle both core and details"""
        with self.uow:
            location_id_str = str(location_id)

            # Get the location first
            location = (
                self.uow.db.query(Location)
                .filter(Location.location_id == location_id_str)
                .first()
            )
            if not location:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Location not found",
                )

            # Update core location fields
            update_data = location_update.dict(exclude_unset=True)
            core_fields = [
                "location_name",
                "address",
                "latitude",
                "longitude",
                "category_id",
                "region_id",
                "district_id",
                "city_id",
                "status",
            ]
            details_fields = [
                "contact_info",
                "website_url",
                "operating_hours",
                "description",
            ]

            # Update core location fields
            for field in core_fields:
                if field in update_data and update_data[field] is not None:
                    setattr(location, field, update_data[field])

            # Update or create location details
            details = (
                self.uow.db.query(LocationDetails)
                .filter(LocationDetails.location_id == location_id_str)
                .first()
            )
            if not details:
                details = LocationDetails(location_id=location_id_str)
                self.uow.db.add(details)

            for field in details_fields:
                if field in update_data and update_data[field] is not None:
                    setattr(details, field, update_data[field])

            self.uow.commit()
            logger.info(
                f"Location {
                    location.location_name} updated by {
                    updated_by.username}")
            return self.get_location_with_details(location_id_str)

    def search_locations(
        self, search: LocationSearch
    ) -> Tuple[List[LocationSearchResponse], int]:
        """Search locations with distance calculation and filtering"""
        query = self.uow.db.query(Location).options(
            joinedload(Location.stats),
            joinedload(Location.category),
            joinedload(Location.images),
        )

        # Apply filters
        if search.filters:
            if search.filters.category_id:
                query = query.filter(
                    Location.category_id == search.filters.category_id
                )
            if search.filters.region_id:
                query = query.filter(
                    Location.region_id == search.filters.region_id
                )
            if search.filters.district_id:
                query = query.filter(
                    Location.district_id == search.filters.district_id
                )
            if search.filters.city_id:
                query = query.filter(
                    Location.city_id == search.filters.city_id
                )
            if search.filters.status:
                query = query.filter(Location.status == search.filters.status)
            if search.filters.min_accessibility_score:
                query = query.join(LocationStats).filter(
                    LocationStats.accessibility_score
                    >= search.filters.min_accessibility_score
                )
            if search.filters.max_accessibility_score:
                query = query.join(LocationStats).filter(
                    LocationStats.accessibility_score
                    <= search.filters.max_accessibility_score
                )

        # Text search
        if search.query:
            search_filter = or_(
                Location.location_name.ilike(f"%{search.query}%"),
                Location.address.ilike(f"%{search.query}%"),
            )
            query = query.filter(search_filter)

        # Distance filtering
        if search.center_lat and search.center_lng and search.radius_km:
            # Haversine formula for distance calculation
            distance_expr = (
                func.acos(
                    func.cos(func.radians(search.center_lat))
                    * func.cos(func.radians(Location.latitude))
                    * func.cos(
                        func.radians(Location.longitude)
                        - func.radians(search.center_lng)
                    )
                    + func.sin(func.radians(search.center_lat))
                    * func.sin(func.radians(Location.latitude))
                )
                * 6371
            )  # Earth radius in km

            query = query.filter(distance_expr <= search.radius_km)
            query = query.add_columns(distance_expr.label("distance_km"))

        # Get total count
        total = query.count()

        # Apply pagination
        locations = query.offset(search.offset).limit(search.limit).all()

        # Convert to response format
        location_responses = []
        for result in locations:
            if isinstance(result, tuple):  # Has distance
                location, distance = result
                distance_km = float(distance) if distance else None
            else:
                location = result
                distance_km = None

            primary_image = None
            if location.images and len(location.images) > 0:
                # Construct full URL for the primary image
                image_key = location.images[0].image_url
                primary_image = f"http://{
                    settings.storage.minio_endpoint}/{
                    settings.storage.minio_bucket}/{image_key}"

            # Safely get category name
            category_name = None
            if location.category:
                category_name = location.category.category_name
            elif location.category_id:
                # Fallback: query category separately if not loaded
                from app.models.category_model import Category

                category = (
                    self.uow.db.query(Category)
                    .filter(Category.category_id == location.category_id)
                    .first()
                )
                category_name = (
                    category.category_name if category else "Unknown Category"
                )

            response_data = {
                "location_id": str(location.location_id),
                "location_name": location.location_name,
                "address": location.address,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "distance_km": distance_km,
                "accessibility_score": (
                    location.stats.accessibility_score
                    if location.stats
                    else None
                ),
                "average_rating": (
                    location.stats.average_rating if location.stats else None
                ),
                "category_name": category_name,
                "primary_image_url": primary_image,
            }
            location_responses.append(LocationSearchResponse(**response_data))

        return location_responses, total

    def get_locations_paginated(
        self, page: int = 1, size: int = 50, filters: LocationFilter = None
    ) -> PaginatedLocations:
        """Get paginated list of locations with filtering"""
        query = self.uow.db.query(Location).options(
            joinedload(Location.stats),
            joinedload(Location.details),  # Add details for contact info, etc.
            joinedload(Location.category),
            joinedload(Location.region),
            joinedload(Location.district),
            joinedload(Location.city),
            joinedload(Location.images),
            joinedload(Location.inspectors).joinedload(LocationInspector.user),  # Add inspector loading
        )

        # Apply filters
        if filters:
            if filters.category_id:
                query = query.filter(
                    Location.category_id == filters.category_id
                )
            if filters.region_id:
                query = query.filter(Location.region_id == filters.region_id)
            if filters.district_id:
                query = query.filter(
                    Location.district_id == filters.district_id
                )
            if filters.city_id:
                query = query.filter(Location.city_id == filters.city_id)
            if filters.status:
                query = query.filter(Location.status == filters.status)
            if filters.min_accessibility_score:
                query = query.join(LocationStats).filter(
                    LocationStats.accessibility_score
                    >= filters.min_accessibility_score
                )
            if filters.has_assessments is not None:
                if filters.has_assessments:
                    query = query.join(LocationStats).filter(
                        LocationStats.last_assessment_date.isnot(None)
                    )
                else:
                    query = query.join(LocationStats).filter(
                        LocationStats.last_assessment_date.is_(None)
                    )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        locations = query.offset(offset).limit(size).all()

        # Preload all categories and regions to avoid N+1 queries
        category_ids = {
            loc.category_id for loc in locations if loc.category_id
        }
        region_ids = {loc.region_id for loc in locations if loc.region_id}

        categories_map = {}
        regions_map = {}

        if category_ids:
            from app.models.category_model import Category

            categories = (
                self.uow.db.query(Category)
                .filter(Category.category_id.in_(category_ids))
                .all()
            )
            categories_map = {
                cat.category_id: cat.category_name for cat in categories
            }

        if region_ids:
            from app.models.region_model import Region

            regions = (
                self.uow.db.query(Region)
                .filter(Region.region_id.in_(region_ids))
                .all()
            )
            regions_map = {reg.region_id: reg.region_name for reg in regions}

        # Convert to response format with proper data loading
        location_responses = []
        for location in locations:
            primary_image = None
            if location.images and len(location.images) > 0:
                # Construct full URL for the primary image
                image_key = location.images[0].image_url
                primary_image = f"http://{
                    settings.storage.minio_endpoint}/{
                    settings.storage.minio_bucket}/{image_key}"

            # Get category name with multiple fallback methods
            category_name = None
            if location.category:
                category_name = location.category.category_name
            elif (
                location.category_id and location.category_id in categories_map
            ):
                category_name = categories_map[location.category_id]
            elif location.category_id:
                # Last resort fallback
                from app.models.category_model import Category

                category = (
                    self.uow.db.query(Category)
                    .filter(Category.category_id == location.category_id)
                    .first()
                )
                category_name = category.category_name if category else None

            # Get region name with multiple fallback methods
            region_name = None
            if location.region:
                region_name = location.region.region_name
            elif location.region_id and location.region_id in regions_map:
                region_name = regions_map[location.region_id]
            elif location.region_id:
                # Last resort fallback
                from app.models.region_model import Region

                region = (
                    self.uow.db.query(Region)
                    .filter(Region.region_id == location.region_id)
                    .first()
                )
                region_name = region.region_name if region else None

            # Get district and city names
            district_name = location.district.district_name if location.district else None
            city_name = location.city.city_name if location.city else None

            response_data = {
                "location_id": str(location.location_id),
                "location_name": location.location_name,
                "address": location.address,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "status": location.status,
                "accessibility_score": (
                    location.stats.accessibility_score
                    if location.stats
                    else None
                ),
                "average_rating": (
                    location.stats.average_rating if location.stats else None
                ),
                "total_reviews": (
                    location.stats.total_reviews if location.stats else 0
                ),
                "category_name": category_name,
                "region_name": region_name,
                "district_name": district_name,
                "city_name": city_name,
                "primary_image_url": primary_image,
                # Add the ID fields needed for editing
                "category_id": location.category_id,
                "region_id": location.region_id,
                "district_id": location.district_id,
                "city_id": location.city_id,
                # Add details fields for editing
                "contact_info": location.details.contact_info if location.details else None,
                "website_url": location.details.website_url if location.details else None,
                "description": location.details.description if location.details else None,
                "operating_hours": location.details.operating_hours if location.details else None,
                # Add inspector count and inspector information
                "inspector_count": len(location.inspectors) if location.inspectors else 0,
                "inspectors": [
                    {
                        "user_id": str(inspector.user_id),
                        "username": inspector.user.username if inspector.user else None,
                        "first_name": (
                            inspector.user.profile.first_name 
                            if inspector.user and inspector.user.profile 
                            else None
                        ),
                        "surname": (
                            inspector.user.profile.surname 
                            if inspector.user and inspector.user.profile 
                            else None
                        ),
                        "email": inspector.user.email if inspector.user else None,
                        "assigned_at": inspector.assigned_at.isoformat() if inspector.assigned_at else None,
                    }
                    for inspector in (location.inspectors or [])
                ],
            }
            location_responses.append(LocationListResponse(**response_data))

        pages = (total + size - 1) // size
        return PaginatedLocations(
            items=location_responses,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    def add_location_to_favourites(
        self, location_id: str, user_id: str
    ) -> bool:
        """Add location to user's favourites"""
        with self.uow:
            # Check if already exists
            existing = (
                self.uow.db.query(Favourite)
                .filter(
                    and_(
                        Favourite.location_id == location_id,
                        Favourite.user_id == user_id,
                    )
                )
                .first()
            )

            if existing:
                return False  # Already in favourites

            favourite = Favourite(user_id=user_id, location_id=location_id)
            self.uow.db.add(favourite)
            self.uow.commit()
            return True

    def remove_location_from_favourites(
        self, location_id: str, user_id: str
    ) -> bool:
        """Remove location from user's favourites"""
        with self.uow:
            favourite = (
                self.uow.db.query(Favourite)
                .filter(
                    and_(
                        Favourite.location_id == location_id,
                        Favourite.user_id == user_id,
                    )
                )
                .first()
            )

            if not favourite:
                return False  # Not in favourites

            self.uow.db.delete(favourite)
            self.uow.commit()
            return True

    def rate_location(
        self, location_id: str, user_id: str, rating_value: int
    ) -> bool:
        """Rate a location and update stats"""
        with self.uow:
            # Check if user already rated this location
            existing_rating = (
                self.uow.db.query(LocationRating)
                .filter(
                    and_(
                        LocationRating.location_id == location_id,
                        LocationRating.user_id == user_id,
                    )
                )
                .first()
            )

            if existing_rating:
                # Update existing rating
                old_value = existing_rating.rating_value
                existing_rating.rating_value = rating_value
            else:
                # Create new rating
                rating = LocationRating(
                    location_id=location_id,
                    user_id=user_id,
                    rating_value=rating_value,
                )
                self.uow.db.add(rating)
                old_value = None

            # Update location stats
            self._update_location_rating_stats(
                location_id, rating_value, old_value
            )

            self.uow.commit()
            return True

    def _update_location_rating_stats(
        self, location_id: str, new_rating: int, old_rating: int = None
    ):
        """Update location rating statistics"""
        stats = (
            self.uow.db.query(LocationStats)
            .filter(LocationStats.location_id == location_id)
            .first()
        )
        if not stats:
            return

        # Get all ratings for this location
        ratings = (
            self.uow.db.query(LocationRating.rating_value)
            .filter(LocationRating.location_id == location_id)
            .all()
        )

        if ratings:
            rating_values = [r[0] for r in ratings]
            stats.total_ratings = len(rating_values)
            stats.average_rating = sum(rating_values) / len(rating_values)
        else:
            stats.total_ratings = 0
            stats.average_rating = None

    def bulk_update_location_status(
        self, location_ids: List[str], status: str, updated_by: User
    ) -> int:
        """Bulk update location status"""
        with self.uow:
            updated_count = (
                self.uow.db.query(Location)
                .filter(Location.location_id.in_(location_ids))
                .update({"status": status}, synchronize_session=False)
            )

            self.uow.commit()
            logger.info(
                f"Bulk updated {updated_count} locations to status {status} by {
                    updated_by.username}")
            return updated_count

    def delete_location(self, location_id: str, deleted_by: User) -> bool:
        """Delete location and all related data (cascading)"""
        with self.uow:
            location = (
                self.uow.db.query(Location)
                .filter(Location.location_id == location_id)
                .first()
            )
            if not location:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Location not found",
                )

            location_name = location.location_name
            self.uow.db.delete(
                location
            )  # Cascade will handle details, stats, images, etc.
            self.uow.commit()

            logger.info(
                f"Location {location_name} deleted by {deleted_by.username}"
            )
            return True

    def get_user_favourites(
        self, user_id: str, page: int = 1, size: int = 50
    ) -> PaginatedLocations:
        """Get user's favourite locations"""
        query = (
            self.uow.db.query(Location)
            .join(Favourite)
            .filter(Favourite.user_id == user_id)
            .options(
                joinedload(Location.stats),
                joinedload(Location.category),
                joinedload(Location.region),
                joinedload(Location.images),
            )
        )

        total = query.count()
        offset = (page - 1) * size
        locations = query.offset(offset).limit(size).all()

        # Convert to response format
        location_responses = []
        for location in locations:
            primary_image = None
            if location.images and len(location.images) > 0:
                # Construct full URL for the primary image
                image_key = location.images[0].image_url
                primary_image = f"http://{
                    settings.storage.minio_endpoint}/{
                    settings.storage.minio_bucket}/{image_key}"

            # Safely get category name
            category_name = None
            if location.category:
                category_name = location.category.category_name
            elif location.category_id:
                # Fallback: query category separately if not loaded
                from app.models.category_model import Category

                category = (
                    self.uow.db.query(Category)
                    .filter(Category.category_id == location.category_id)
                    .first()
                )
                category_name = (
                    category.category_name if category else "Unknown Category"
                )

            # Safely get region name
            region_name = None
            if location.region:
                region_name = location.region.region_name
            elif location.region_id:
                # Fallback: query region separately if not loaded
                from app.models.region_model import Region

                region = (
                    self.uow.db.query(Region)
                    .filter(Region.region_id == location.region_id)
                    .first()
                )
                region_name = (
                    region.region_name if region else "Unknown Region"
                )

            response_data = {
                "location_id": str(location.location_id),
                "location_name": location.location_name,
                "address": location.address,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "status": location.status,
                "accessibility_score": (
                    location.stats.accessibility_score
                    if location.stats
                    else None
                ),
                "average_rating": (
                    location.stats.average_rating if location.stats else None
                ),
                "total_reviews": (
                    location.stats.total_reviews if location.stats else 0
                ),
                "category_name": category_name,
                "region_name": region_name,
                "primary_image_url": primary_image,
            }
            location_responses.append(LocationListResponse(**response_data))

        pages = (total + size - 1) // size
        return PaginatedLocations(
            items=location_responses,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    # ---------------- Inspector management ---------------------------
    def assign_inspector(
        self, current_user: User, loc_id: UUID, inspector_id: UUID
    ):
        """Assign an inspector to a location - only superadmin can do this."""
        # Only superadmin (role_id=1) can assign inspectors
        if current_user.role_id != 1:
            raise HTTPException(
                status_code=403, detail="Only superadmin can assign inspectors"
            )

        # Get the user being assigned as inspector
        inspector_user = self.uow.users.get(inspector_id)
        if not inspector_user:
            raise HTTPException(
                status_code=404, detail="Inspector user not found"
            )

        # Only users with role_id=1 (superadmin) or role_id=2 (admin) can be
        # assigned as inspectors
        if inspector_user.role_id not in [1, 2]:
            raise HTTPException(
                status_code=400,
                detail="Only admin and superadmin users can be assigned as inspectors",
            )

        # Admin users can't assign themselves as inspectors
        if current_user.user_id == inspector_id and current_user.role_id == 2:
            raise HTTPException(
                status_code=400,
                detail="Admin users cannot assign themselves as inspectors",
            )

        with self.uow:
            self.uow.locations.assign_inspector(
                self.ensure_uuid(loc_id), self.ensure_uuid(inspector_id)
            )
            self.uow.commit()

    def unassign_inspector(
        self, current_user: User, loc_id: UUID, inspector_id: UUID
    ):
        """Remove an inspector from a location - only superadmin can do this."""
        # Only superadmin (role_id=1) can remove inspectors
        if current_user.role_id != 1:
            raise HTTPException(
                status_code=403, detail="Only superadmin can remove inspectors"
            )

        with self.uow:
            self.uow.locations.unassign_inspector(
                self.ensure_uuid(loc_id), self.ensure_uuid(inspector_id)
            )
            self.uow.commit()

    # ---------------- internal helper --------------------------------
    def _require_admin(self, user: User):
        if user.role_id not in [1, 2]:  # 1 = superadmin, 2 = admin
            raise HTTPException(
                status_code=403, detail="Admin access required"
            )

    def update_accessibility_score(self, location_id: UUID) -> Optional[float]:
        """Update the location's accessibility_score based on verified assessments."""
        with self.uow:
            from sqlalchemy import text

            # Calculate average score from verified assessments
            result = self.uow.db.execute(
                text(
                    """
                SELECT AVG(CAST(overall_score AS FLOAT)) as avg_score
                FROM location_set_assessments
                WHERE location_id = :location_id
                AND status = 'verified'
                AND overall_score IS NOT NULL
            """
                ),
                {"location_id": str(location_id)},
            )

            row = result.fetchone()
            avg_score = (
                row.avg_score if row and row.avg_score is not None else 0.0
            )

            # Update the LocationStats table, not the Location table
            from app.models.location_model import LocationStats

            stats = (
                self.uow.db.query(LocationStats)
                .filter(LocationStats.location_id == str(location_id))
                .first()
            )
            if stats:
                stats.accessibility_score = float(avg_score)
                self.uow.commit()
                logger.info(
                    f"Updated accessibility_score for location {location_id}: {avg_score}")
                return float(avg_score)
            else:
                # Create stats record if it doesn't exist
                stats = LocationStats(
                    location_id=str(location_id),
                    accessibility_score=float(avg_score),
                    total_reviews=0,
                    total_ratings=0,
                )
                self.uow.db.add(stats)
                self.uow.commit()
                logger.info(
                    f"Created stats record and set accessibility_score for location {location_id}: {avg_score}")
                return float(avg_score)

    def get_popular_locations(self, limit: int = 10) -> List[LocationResponse]:
        """Get popular locations with complete data."""
        locations = (
            self.uow.db.query(Location)
            .options(
                joinedload(Location.details),
                joinedload(Location.stats),
                joinedload(Location.images),
                joinedload(Location.category),
                joinedload(Location.region),
                joinedload(Location.district),
                joinedload(Location.city),
            )
            .limit(limit)
            .all()
        )

        # Convert to LocationResponse objects with proper UUID to string
        # conversion
        response_locations = []
        for location in locations:
            # Build location dict with string IDs
            location_data = {
                "location_id": str(location.location_id),
                "location_name": location.location_name,
                "address": location.address,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "category_id": location.category_id,
                "region_id": location.region_id,
                "district_id": location.district_id,
                "city_id": location.city_id,
                "status": location.status,
                "created_at": location.created_at,
                "updated_at": location.updated_at,
                "details": None,
                "stats": None,
                "images": [],
            }

            # Add details if present
            if location.details:
                location_data["details"] = {
                    "location_id": str(location.details.location_id),
                    "contact_info": location.details.contact_info,
                    "website_url": location.details.website_url,
                    "operating_hours": location.details.operating_hours,
                    "description": location.details.description,
                    "created_at": location.details.created_at,
                    "updated_at": location.details.updated_at,
                }

            # Add stats if present
            if location.stats:
                location_data["stats"] = {
                    "location_id": str(
                        location.stats.location_id),
                    "accessibility_score": location.stats.accessibility_score,
                    "total_reviews": location.stats.total_reviews,
                    "total_ratings": location.stats.total_ratings,
                    "average_rating": location.stats.average_rating,
                    "last_assessment_date": location.stats.last_assessment_date,
                    "updated_at": location.stats.updated_at,
                }

            # Add images if present
            if location.images:
                for image in location.images:
                    location_data["images"].append(
                        {
                            "image_id": image.image_id,
                            "location_id": str(image.location_id),
                            "image_url": image.image_url,
                            "description": image.description,
                            "position": image.position,
                            "created_at": image.created_at,
                        }
                    )

            response_locations.append(LocationResponse(**location_data))
        return response_locations

    def get_recently_rated_locations(
        self, limit: int = 10
    ) -> List[LocationResponse]:
        """Get recently rated locations with complete data."""
        locations = (
            self.uow.db.query(Location)
            .options(
                joinedload(Location.details),
                joinedload(Location.stats),
                joinedload(Location.images),
                joinedload(Location.category),
                joinedload(Location.region),
                joinedload(Location.district),
                joinedload(Location.city),
            )
            .limit(limit)
            .all()
        )

        # Convert to LocationResponse objects with proper UUID to string
        # conversion
        response_locations = []
        for location in locations:
            # Build location dict with string IDs
            location_data = {
                "location_id": str(location.location_id),
                "location_name": location.location_name,
                "address": location.address,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "category_id": location.category_id,
                "region_id": location.region_id,
                "district_id": location.district_id,
                "city_id": location.city_id,
                "status": location.status,
                "created_at": location.created_at,
                "updated_at": location.updated_at,
                "details": None,
                "stats": None,
                "images": [],
            }

            # Add details if present
            if location.details:
                location_data["details"] = {
                    "location_id": str(location.details.location_id),
                    "contact_info": location.details.contact_info,
                    "website_url": location.details.website_url,
                    "operating_hours": location.details.operating_hours,
                    "description": location.details.description,
                    "created_at": location.details.created_at,
                    "updated_at": location.details.updated_at,
                }

            # Add stats if present
            if location.stats:
                location_data["stats"] = {
                    "location_id": str(
                        location.stats.location_id),
                    "accessibility_score": location.stats.accessibility_score,
                    "total_reviews": location.stats.total_reviews,
                    "total_ratings": location.stats.total_ratings,
                    "average_rating": location.stats.average_rating,
                    "last_assessment_date": location.stats.last_assessment_date,
                    "updated_at": location.stats.updated_at,
                }

            # Add images if present
            if location.images:
                for image in location.images:
                    location_data["images"].append(
                        {
                            "image_id": image.image_id,
                            "location_id": str(image.location_id),
                            "image_url": image.image_url,
                            "description": image.description,
                            "position": image.position,
                            "created_at": image.created_at,
                        }
                    )

            response_locations.append(LocationResponse(**location_data))
        return response_locations

    # Location interaction methods
    def get_location_ratings(self, location_id: UUID) -> List[dict]:
        """Get ratings for a location."""
        from app.services.rating_service import RatingService

        rating_service = RatingService(self.uow)
        ratings = rating_service.get_location_ratings(location_id)

        # Convert to dict for JSON response
        return [rating.dict() for rating in ratings]

    def add_rating(
        self,
        location_id: UUID,
        rating: float,
        comment: str = None,
        current_user: User = None,
    ):
        """Add rating to location."""
        if not current_user:
            raise HTTPException(
                status_code=401, detail="Authentication required"
            )

        from app.schemas.rating_schema import RatingCreate
        from app.services.rating_service import RatingService

        rating_service = RatingService(self.uow)
        payload = RatingCreate(
            location_id=location_id, rating=rating, comment=comment
        )

        result = rating_service.add_rating(payload, current_user)

        # Update location's average rating
        self.update_location_average_rating(location_id)

        return result.dict()

    def get_location_stats(self, location_id: UUID) -> dict:
        """Get real stats for a location."""
        from app.services.rating_service import RatingService
        from app.services.social_service import SocialService

        rating_service = RatingService(self.uow)
        SocialService(self.uow)

        # Get rating stats
        rating_stats = rating_service.get_location_rating_stats(location_id)

        # Get favorites count (approximate - you might want to add this method
        # to social service)
        favorites_count = 0  # placeholder - implement if needed

        # Get location accessibility score
        location = self.uow.locations.get(location_id)
        accessibility_score = (
            location.stats.accessibility_score
            if location and location.stats
            else 0.0
        )

        return {
            "total_ratings": rating_stats.total_ratings,
            "average_rating": rating_stats.average_rating,
            "total_favorites": favorites_count,
            "total_comments": rating_stats.total_ratings,  # Comments come with ratings
            "accessibility_score": accessibility_score,
            "rating_distribution": rating_stats.rating_distribution,
        }

    def get_favorite_status(
        self, location_id: UUID, current_user: User
    ) -> dict:
        """Get favorite status for a location for the current user."""
        existing_fav = self.uow.favourites.get_user_fav(
            current_user.user_id, location_id
        )
        return {"is_favorited": existing_fav is not None}

    def update_location_average_rating(self, location_id: UUID):
        """Update location's cached average rating."""
        from app.services.rating_service import RatingService

        rating_service = RatingService(self.uow)
        rating_service.get_location_rating_stats(location_id)

        # Update the location's cached average rating
        location = self.uow.locations.get(location_id)
        if location:
            # You might want to add an average_rating field to the Location model
            # location.average_rating = stats.average_rating
            # For now, we can use accessibility_score to store it temporarily
            # or add a new field for user ratings vs accessibility ratings
            pass

    def add_to_favorites(self, location_id: UUID, current_user: User):
        """Add location to favorites using social service."""
        from app.schemas.social_schema import FavouriteSchema
        from app.services.social_service import SocialService

        social_service = SocialService(self.uow)
        payload = FavouriteSchema.Toggle(location_id=location_id)

        # Check if already favorited
        existing_fav = self.uow.favourites.get_user_fav(
            current_user.user_id, location_id
        )

        if existing_fav:
            return {
                "message": "Location already in favorites",
                "is_favorited": True,
            }

        # Add to favorites
        added = social_service.toggle_favourite(payload, current_user)
        return {"message": "Added to favorites", "is_favorited": added}

    def remove_from_favorites(self, location_id: UUID, current_user: User):
        """Remove location from favorites using social service."""
        from app.schemas.social_schema import FavouriteSchema
        from app.services.social_service import SocialService

        social_service = SocialService(self.uow)
        payload = FavouriteSchema.Toggle(location_id=location_id)

        # Check if exists
        existing_fav = self.uow.favourites.get_user_fav(
            current_user.user_id, location_id
        )

        if not existing_fav:
            return {
                "message": "Location not in favorites",
                "is_favorited": False,
            }

        # Remove from favorites
        removed = social_service.toggle_favourite(payload, current_user)
        return {"message": "Removed from favorites", "is_favorited": removed}

    def _process_locations_for_output(
        self, locations: List[Location | dict]
    ) -> List[dict]:
        processed_locations = []
        for loc_entry in locations:
            # Convert Location object to dict using LocationListResponse schema
            if isinstance(loc_entry, Location):
                # Create a dict with the required fields
                loc_data = {
                    "location_id": loc_entry.location_id,
                    "location_name": loc_entry.location_name,
                    "address": loc_entry.address,
                    "latitude": loc_entry.latitude,
                    "longitude": loc_entry.longitude,
                    "status": loc_entry.status,
                    "accessibility_score": (
                        getattr(loc_entry.stats, "accessibility_score", None)
                        if hasattr(loc_entry, "stats") and loc_entry.stats
                        else None
                    ),
                    "average_rating": (
                        getattr(loc_entry.stats, "average_rating", None)
                        if hasattr(loc_entry, "stats") and loc_entry.stats
                        else None
                    ),
                    "total_reviews": (
                        getattr(loc_entry.stats, "total_reviews", 0)
                        if hasattr(loc_entry, "stats") and loc_entry.stats
                        else 0
                    ),
                    "category_name": (
                        getattr(loc_entry.category, "category_name", None)
                        if hasattr(loc_entry, "category")
                        and loc_entry.category
                        else None
                    ),
                    "region_name": (
                        getattr(loc_entry.region, "region_name", None)
                        if hasattr(loc_entry, "region") and loc_entry.region
                        else None
                    ),
                    "primary_image_url": (
                        loc_entry.images[0].image_url
                        if hasattr(loc_entry, "images") and loc_entry.images
                        else None
                    ),
                }
            else:
                # If it's already a dict, use it as is
                loc_data = loc_entry

            # Patch image URLs if needed
            if loc_data.get("primary_image_url"):
                loc_data["primary_image_url"] = (
                    f'{settings.storage.minio_endpoint}/{settings.storage.minio_bucket}/{loc_data["primary_image_url"]}'
                )

            processed_locations.append(loc_data)
        return processed_locations

    def get_location(self, location_id: UUID) -> Optional[LocationResponse]:
        """Get location - alias for get_location_with_details with UUID support"""
        return self.get_location_with_details(str(location_id))

    @cache.cacheable(
        lambda self, category_id: f"locations:category:{category_id}", ttl=300
    )
    def get_locations_by_category(
        self, category_id: int
    ) -> List[LocationResponse]:
        """Get all locations for a specific category - CACHED."""
        locations = (
            self.uow.db.query(Location)
            .options(
                joinedload(Location.details),
                joinedload(Location.stats),
                joinedload(Location.images),
                joinedload(Location.category),
                joinedload(Location.region),
                joinedload(Location.district),
                joinedload(Location.city),
            )
            .filter(Location.category_id == category_id)
            .all()
        )

        return [LocationResponse.from_orm(location) for location in locations]

    @cache.cacheable(
        lambda self, region_id: f"locations:region:{region_id}", ttl=300
    )
    def get_locations_by_region(
        self, region_id: int
    ) -> List[LocationResponse]:
        """Get all locations in a specific region - CACHED."""
        locations = (
            self.uow.db.query(Location)
            .options(
                joinedload(Location.details),
                joinedload(Location.stats),
                joinedload(Location.images),
                joinedload(Location.category),
                joinedload(Location.region),
                joinedload(Location.district),
                joinedload(Location.city),
            )
            .filter(Location.region_id == region_id)
            .all()
        )

        return [LocationResponse.from_orm(location) for location in locations]

    @cache.cacheable(
        lambda self, district_id: f"locations:district:{district_id}", ttl=300
    )
    def get_locations_by_district(
        self, district_id: int
    ) -> List[LocationResponse]:
        """Get all locations in a specific district - CACHED."""
        locations = (
            self.uow.db.query(Location)
            .options(
                joinedload(Location.details),
                joinedload(Location.stats),
                joinedload(Location.images),
                joinedload(Location.category),
                joinedload(Location.region),
                joinedload(Location.district),
                joinedload(Location.city),
            )
            .filter(Location.district_id == district_id)
            .all()
        )

        return [LocationResponse.from_orm(location) for location in locations]

    @cache.cacheable(
        lambda self, city_id: f"locations:city:{city_id}", ttl=300
    )
    def get_locations_by_city(self, city_id: int) -> List[LocationResponse]:
        """Get all locations in a specific city - CACHED."""
        locations = (
            self.uow.db.query(Location)
            .options(
                joinedload(Location.details),
                joinedload(Location.stats),
                joinedload(Location.images),
                joinedload(Location.category),
                joinedload(Location.region),
                joinedload(Location.district),
                joinedload(Location.city),
            )
            .filter(Location.city_id == city_id)
            .all()
        )

        return [LocationResponse.from_orm(location) for location in locations]
