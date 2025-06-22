import re

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.domain.unit_of_work import UnitOfWork
from app.models.city_model import City
from app.models.district_model import District
from app.models.region_model import Region
from app.schemas.geo_schema import CitySchema, DistrictSchema, RegionSchema
from app.utils.cache import cache


def handle_integrity_error(error, entity_name: str, unique_fields: dict):
    msg = str(error.orig)
    for field, label in unique_fields.items():
        if field in msg:
            raise HTTPException(
                status_code=400,
                detail=f"{entity_name} with this {label} already exists.",
            )
    # fallback
    raise HTTPException(
        status_code=400,
        detail=f"{entity_name} already exists or unique constraint failed.",
    )


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()) if name else name


class GeoService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # -------- Region --------------------------------------------------
    def create_region(self, payload: RegionSchema.Create) -> Region:
        with self.uow:
            data = payload.dict()
            data["region_name"] = normalize_name(data["region_name"])
            region = Region(**data)
            self.uow.regions.add(region)
            try:
                self.uow.commit()
                # Invalidate regions cache after creating new region
                cache.invalidate("regions")
            except IntegrityError as e:
                self.uow.rollback()
                handle_integrity_error(
                    e, "Region", {"region_code": "code", "region_name": "name"}
                )
            return region

    @cache.cacheable(
        lambda self, limit=10, offset=0: f"regions:list:{limit}:{offset}",
        ttl=3600,
    )  # Cache for 1 hour
    def get_regions(self, limit: int = 10, offset: int = 0):
        """Get paginated regions."""
        items, total = self.uow.regions.get_paginated(limit, offset)

        # Convert SQLAlchemy models to dictionaries for better caching
        serialized_items = []
        for region in items:
            serialized_items.append(
                {
                    "region_id": region.region_id,
                    "region_name": region.region_name,
                    "region_code": region.region_code,
                    "description": region.description,
                    "area": (
                        float(region.area) if region.area is not None else None
                    ),
                    "population": region.population,
                    "created_at": (
                        region.created_at.isoformat()
                        if region.created_at
                        else None
                    ),
                }
            )

        return {"items": serialized_items, "total": total}

    @cache.cacheable(lambda self, region_id: f"regions:{region_id}", ttl=3600)
    def get_region(self, region_id: int):
        """Get a specific region by ID."""
        region = self.uow.regions.get(region_id)
        if not region:
            raise HTTPException(404, "Region not found")

        # Convert to dictionary for better caching
        return {
            "region_id": region.region_id,
            "region_name": region.region_name,
            "region_code": region.region_code,
            "description": region.description,
            "area": float(region.area) if region.area is not None else None,
            "population": region.population,
            "created_at": (
                region.created_at.isoformat() if region.created_at else None
            ),
        }

    def update_region(
        self, region_id: int, payload: RegionSchema.Create
    ) -> Region:
        with self.uow:
            region = self.uow.regions.get(region_id)
            if not region:
                raise HTTPException(404, "Region not found")
            data = payload.dict()
            data["region_name"] = normalize_name(data["region_name"])
            for key, value in data.items():
                setattr(region, key, value)
            try:
                self.uow.commit()
                # Invalidate specific region cache and regions list cache
                cache.invalidate(f"regions:{region_id}")
                cache.invalidate("regions:list")
            except IntegrityError as e:
                self.uow.rollback()
                handle_integrity_error(
                    e, "Region", {"region_code": "code", "region_name": "name"}
                )
            return region

    def delete_region(self, region_id: int):
        with self.uow:
            region = self.uow.regions.get(region_id)
            if not region:
                raise HTTPException(404, "Region not found")
            self.uow.regions.delete(region)
            self.uow.commit()
            # Invalidate region caches
            cache.invalidate(f"regions:{region_id}")
            cache.invalidate("regions:list")
            # Also invalidate districts that were in this region
            cache.invalidate("districts")
            return {"detail": "Region deleted"}

    # -------- District ------------------------------------------------
    def create_district(self, payload: DistrictSchema.Create) -> District:
        with self.uow:
            data = payload.dict()
            data["district_name"] = normalize_name(data["district_name"])
            district = District(**data)
            self.uow.districts.add(district)
            try:
                self.uow.commit()
                # Invalidate districts cache after creating new district
                cache.invalidate("districts")
            except IntegrityError as e:
                self.uow.rollback()
                handle_integrity_error(
                    e,
                    "District",
                    {"district_code": "code", "district_name": "name"},
                )
            return district

    @cache.cacheable(lambda self,
                     region_id=None,
                     limit=10,
                     offset=0: f"districts:list:{region_id or 'all'}:{limit}:{offset}",
                     ttl=3600,
                     )
    def get_districts(
        self, region_id: int = None, limit: int = 10, offset: int = 0
    ):
        """Get paginated districts, optionally filtered by region."""
        if region_id:
            # For filtered, return all in region (no pagination for now)
            items = self.uow.districts.in_region(region_id)
            total = len(items)
        else:
            items, total = self.uow.districts.get_paginated(limit, offset)

        # Convert SQLAlchemy models to dictionaries for better caching
        serialized_items = []
        for district in items:
            serialized_items.append(
                {
                    "district_id": district.district_id,
                    "district_name": district.district_name,
                    "district_code": district.district_code,
                    "description": district.description,
                    "area": (
                        float(district.area)
                        if district.area is not None
                        else None
                    ),
                    "population": district.population,
                    "region_id": district.region_id,
                    "created_at": (
                        district.created_at.isoformat()
                        if district.created_at
                        else None
                    ),
                }
            )

        return {"items": serialized_items, "total": total}

    @cache.cacheable(
        lambda self, district_id: f"districts:{district_id}", ttl=3600
    )
    def get_district(self, district_id: int):
        """Get a specific district by ID."""
        district = self.uow.districts.get(district_id)
        if not district:
            raise HTTPException(404, "District not found")

        # Convert to dictionary for better caching
        return {
            "district_id": district.district_id,
            "district_name": district.district_name,
            "district_code": district.district_code,
            "description": district.description,
            "area": (
                float(district.area) if district.area is not None else None
            ),
            "population": district.population,
            "region_id": district.region_id,
            "created_at": (
                district.created_at.isoformat()
                if district.created_at
                else None
            ),
        }

    def update_district(
        self, district_id: int, payload: DistrictSchema.Create
    ) -> District:
        with self.uow:
            district = self.uow.districts.get(district_id)
            if not district:
                raise HTTPException(404, "District not found")
            data = payload.dict()
            data["district_name"] = normalize_name(data["district_name"])
            for key, value in data.items():
                setattr(district, key, value)
            try:
                self.uow.commit()
                # Invalidate district caches
                cache.invalidate(f"districts:{district_id}")
                cache.invalidate("districts:list")
            except IntegrityError as e:
                self.uow.rollback()
                handle_integrity_error(
                    e,
                    "District",
                    {"district_code": "code", "district_name": "name"},
                )
            return district

    def delete_district(self, district_id: int):
        with self.uow:
            district = self.uow.districts.get(district_id)
            if not district:
                raise HTTPException(404, "District not found")
            self.uow.districts.delete(district)
            self.uow.commit()
            # Invalidate district caches
            cache.invalidate(f"districts:{district_id}")
            cache.invalidate("districts:list")
            # Also invalidate cities in this district
            cache.invalidate("cities")
            return {"detail": "District deleted"}

    # -------- City ----------------------------------------------------
    def create_city(self, payload: CitySchema.Create) -> City:
        with self.uow:
            data = payload.dict()
            data["city_name"] = normalize_name(data["city_name"])
            city = City(**data)
            self.uow.cities.add(city)
            try:
                self.uow.commit()
                # Invalidate cities cache after creating new city
                cache.invalidate("cities")
            except IntegrityError as e:
                self.uow.rollback()
                handle_integrity_error(
                    e, "City", {"city_code": "code", "city_name": "name"}
                )
            return city

    @cache.cacheable(lambda self,
                     district_id=None,
                     limit=10,
                     offset=0: f"cities:list:{district_id or 'all'}:{limit}:{offset}",
                     ttl=3600,
                     )
    def get_cities(
        self, district_id: int = None, limit: int = 10, offset: int = 0
    ):
        """Get paginated cities, optionally filtered by district."""
        if district_id:
            # For filtered, return all in district (no pagination for now)
            items = self.uow.cities.in_district(district_id)
            total = len(items)
        else:
            items, total = self.uow.cities.get_paginated(limit, offset)

        # Convert SQLAlchemy models to dictionaries for better caching
        serialized_items = []
        for city in items:
            serialized_items.append(
                {
                    "city_id": city.city_id,
                    "city_name": city.city_name,
                    "city_code": city.city_code,
                    "region_id": city.region_id,
                    "district_id": city.district_id,
                    "population": city.population,
                    "created_at": (
                        city.created_at.isoformat()
                        if city.created_at
                        else None
                    ),
                }
            )

        return {"items": serialized_items, "total": total}

    @cache.cacheable(lambda self, city_id: f"cities:{city_id}", ttl=3600)
    def get_city(self, city_id: int):
        """Get a specific city by ID."""
        city = self.uow.cities.get(city_id)
        if not city:
            raise HTTPException(404, "City not found")

        # Convert to dictionary for better caching
        return {
            "city_id": city.city_id,
            "city_name": city.city_name,
            "city_code": city.city_code,
            "region_id": city.region_id,
            "district_id": city.district_id,
            "population": city.population,
            "created_at": (
                city.created_at.isoformat() if city.created_at else None
            ),
        }

    def update_city(self, city_id: int, payload: CitySchema.Create) -> City:
        with self.uow:
            city = self.uow.cities.get(city_id)
            if not city:
                raise HTTPException(404, "City not found")
            data = payload.dict()
            data["city_name"] = normalize_name(data["city_name"])
            for key, value in data.items():
                setattr(city, key, value)
            try:
                self.uow.commit()
                # Invalidate city caches
                cache.invalidate(f"cities:{city_id}")
                cache.invalidate("cities:list")
            except IntegrityError as e:
                self.uow.rollback()
                handle_integrity_error(
                    e, "City", {"city_code": "code", "city_name": "name"}
                )
            return city

    def delete_city(self, city_id: int):
        with self.uow:
            city = self.uow.cities.get(city_id)
            if not city:
                raise HTTPException(404, "City not found")
            self.uow.cities.delete(city)
            self.uow.commit()
            # Invalidate city caches
            cache.invalidate(f"cities:{city_id}")
            cache.invalidate("cities:list")
            return {"detail": "City deleted"}
