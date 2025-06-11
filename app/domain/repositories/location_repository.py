from __future__ import annotations

import time
from typing import Dict, List, Optional, Sequence, Any
from uuid import UUID

from sqlalchemy import and_, delete, or_, select, text, Index
from sqlalchemy.orm import Session, joinedload, selectinload

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.location_inspector_model import LocationInspector
from app.models.location_model import Location, LocationDetails, LocationStats

from app.utils.cache import cache
from app.utils.logger import get_logger

logger = get_logger("location_repository")


class LocationRepository(SQLAlchemyRepository[Location, UUID]):
    def __init__(self, db: Session):
        super().__init__(Location, db)

    # ---------- query methods -----------------------------------------------
    def get_full(self, location_id: UUID) -> Location | None:
        """Get a location with all related data loaded."""
        start_time = time.time()
        logger.info(f"Repository: Fetching location {location_id} with related data")
        
        # Use selectinload for better performance than joinedload
        stmt = (
            select(Location)
            .options(
                selectinload(Location.details),
                selectinload(Location.stats),
                selectinload(Location.images), 
                selectinload(Location.inspectors).selectinload(LocationInspector.user)
            )
            .where(Location.location_id == str(location_id))
        )
        
        result = self.db.scalar(stmt)
        end_time = time.time()
        logger.info(f"Repository: Location query completed in {end_time - start_time:.2f} seconds")
        return result

    @cache.cacheable(lambda self, **kwargs: f"locations_filter:{hash(str(sorted(kwargs.items())))}", ttl=300)
    def filter_by(self, **kwargs) -> List[Location]:
        """Filter locations by provided criteria."""
        start_time = time.time()
        logger.info(f"Repository: Filtering locations with criteria: {kwargs}")
        
        # Start with a base query
        query = select(Location)
        
        # Only load relations if not a list query with many results
        if kwargs.get("location_id") or kwargs.get("search"):
            query = query.options(
                selectinload(Location.details),
                selectinload(Location.stats),
                selectinload(Location.images), 
                selectinload(Location.inspectors).selectinload(LocationInspector.user)
            )
        else:
            # For list queries, load images and inspectors for location cards
            query = query.options(
                selectinload(Location.details),
                selectinload(Location.stats),
                selectinload(Location.images),
                selectinload(Location.inspectors).selectinload(LocationInspector.user)
            )

        # Handle search separately as it's a special case
        search_term = kwargs.pop("search", None)
        if search_term:
            # Need to join with LocationDetails to search description
            query = query.outerjoin(LocationDetails, Location.location_id == LocationDetails.location_id)
            search_filter = or_(
                Location.location_name.ilike(f"%{search_term}%"),
                Location.address.ilike(f"%{search_term}%"),
                LocationDetails.description.ilike(f"%{search_term}%"),
            )
            query = query.where(search_filter)

        # Handle min_score separately - need to join with LocationStats
        min_score = kwargs.pop("min_score", None)
        if min_score is not None:
            query = query.join(LocationStats, Location.location_id == LocationStats.location_id)
            query = query.where(LocationStats.accessibility_score >= min_score)

        # Add filters for all other fields
        filters = []
        for key, value in kwargs.items():
            if value is not None:
                filters.append(getattr(Location, key) == value)

        if filters:
            query = query.where(and_(*filters))

        result = self.db.scalars(query).unique().all()
        end_time = time.time()
        logger.info(f"Repository: Location filtering completed in {end_time - start_time:.2f} seconds, found {len(result)} locations")
        return result

    @cache.cacheable(lambda self, category_id: f"locations_category:{category_id}", ttl=300)
    def get_by_category(self, category_id: int) -> List[Location]:
        """Get locations by category ID."""
        return self.filter_by(category_id=category_id)

    @cache.cacheable(lambda self, region_id: f"locations_region:{region_id}", ttl=300)
    def get_by_region(self, region_id: int) -> List[Location]:
        """Get locations by region ID."""
        return self.filter_by(region_id=region_id)

    @cache.cacheable(lambda self, district_id: f"locations_district:{district_id}", ttl=300)
    def get_by_district(self, district_id: int) -> List[Location]:
        """Get locations by district ID."""
        return self.filter_by(district_id=district_id)

    @cache.cacheable(lambda self, city_id: f"locations_city:{city_id}", ttl=300)
    def get_by_city(self, city_id: int) -> List[Location]:
        """Get locations by city ID."""
        return self.filter_by(city_id=city_id)

    # ---------- Inspector management -----------------------------------------------
    def assign_inspector(self, location_id: UUID, user_id: UUID) -> None:
        """Assign a user as an inspector to a location."""
        li = LocationInspector(location_id=str(location_id), user_id=str(user_id))
        self.db.merge(li)
        # Invalidate location cache when inspector is assigned
        cache.invalidate(f"location:{str(location_id)}")

    def remove_inspector(self, location_id: UUID, user_id: UUID) -> None:
        """Remove a user from being an inspector of a location."""
        stmt = delete(LocationInspector).where(
            LocationInspector.location_id == str(location_id),
            LocationInspector.user_id == str(user_id),
        )
        self.db.execute(stmt)
        # Invalidate location cache when inspector is removed
        cache.invalidate(f"location:{str(location_id)}")

    def unassign_inspector(self, location_id: UUID, user_id: UUID) -> None:
        """Alias for remove_inspector for consistency."""
        self.remove_inspector(location_id, user_id)

    def get_locations_for_inspector(self, user_id: UUID) -> List[Location]:
        """Get all locations that a user is an inspector for."""
        stmt = (
            select(Location)
            .join(LocationInspector, Location.location_id == LocationInspector.location_id)
            .where(LocationInspector.user_id == str(user_id))
            .options(
                selectinload(Location.details),
                selectinload(Location.stats),
                selectinload(Location.images),
                selectinload(Location.inspectors).selectinload(LocationInspector.user)
            )
        )
        return self.db.scalars(stmt).all()
