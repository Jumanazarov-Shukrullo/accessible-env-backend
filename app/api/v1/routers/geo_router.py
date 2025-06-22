from fastapi import APIRouter, Depends, Query, status

from app.api.v1.dependencies import get_uow
from app.core.auth import auth_manager
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.geo_schema import (
    CitySchema,
    DistrictSchema,
    PaginatedCities,
    PaginatedDistricts,
    PaginatedRegions,
    RegionSchema,
)
from app.services.geo_service import GeoService
from app.utils.logger import get_logger


logger = get_logger("geo_router")


class GeoRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/geo", tags=["Geo"])
        self._register()

    def _register(self):
        self.router.post(
            "/regions",
            response_model=RegionSchema.Out,
            status_code=status.HTTP_201_CREATED,
        )(self._create_region)
        self.router.post(
            "/districts",
            response_model=DistrictSchema.Out,
            status_code=status.HTTP_201_CREATED,
        )(self._create_district)
        self.router.post(
            "/cities",
            response_model=CitySchema.Out,
            status_code=status.HTTP_201_CREATED,
        )(self._create_city)
        self.router.get("/regions", response_model=PaginatedRegions)(
            self._get_regions
        )
        self.router.get(
            "/regions/{region_id}", response_model=RegionSchema.Out
        )(self._get_region)
        self.router.get("/districts", response_model=PaginatedDistricts)(
            self._get_districts
        )
        self.router.get(
            "/districts/{district_id}", response_model=DistrictSchema.Out
        )(self._get_district)
        self.router.get("/cities", response_model=PaginatedCities)(
            self._get_cities
        )
        self.router.get("/cities/{city_id}", response_model=CitySchema.Out)(
            self._get_city
        )
        self.router.put(
            "/regions/{region_id}", response_model=RegionSchema.Out
        )(self._update_region)
        self.router.delete("/regions/{region_id}", status_code=204)(
            self._delete_region
        )
        self.router.put(
            "/districts/{district_id}", response_model=DistrictSchema.Out
        )(self._update_district)
        self.router.delete("/districts/{district_id}", status_code=204)(
            self._delete_district
        )
        self.router.put("/cities/{city_id}", response_model=CitySchema.Out)(
            self._update_city
        )
        self.router.delete("/cities/{city_id}", status_code=204)(
            self._delete_city
        )

    async def _create_region(
        self,
        payload: RegionSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Creating region")
        return GeoService(uow).create_region(payload)

    async def _create_district(
        self,
        payload: DistrictSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Creating district")
        return GeoService(uow).create_district(payload)

    async def _create_city(
        self,
        payload: CitySchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Creating city")
        return GeoService(uow).create_city(payload)

    async def _get_regions(
        self,
        uow: UnitOfWork = Depends(get_uow),
        limit: int = Query(10, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        logger.info("Getting regions")
        return GeoService(uow).get_regions(limit=limit, offset=offset)

    async def _get_region(
        self, region_id: int, uow: UnitOfWork = Depends(get_uow)
    ):
        logger.info(f"Getting region {region_id}")
        return GeoService(uow).get_region(region_id)

    async def _get_districts(
        self,
        region_id: int = Query(None, description="Filter by region ID"),
        uow: UnitOfWork = Depends(get_uow),
        limit: int = Query(10, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        logger.info("Getting districts")
        return GeoService(uow).get_districts(
            region_id, limit=limit, offset=offset
        )

    async def _get_district(
        self, district_id: int, uow: UnitOfWork = Depends(get_uow)
    ):
        logger.info(f"Getting district {district_id}")
        return GeoService(uow).get_district(district_id)

    async def _get_cities(
        self,
        district_id: int = Query(None, description="Filter by district ID"),
        uow: UnitOfWork = Depends(get_uow),
        limit: int = Query(10, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        logger.info("Getting cities")
        return GeoService(uow).get_cities(
            district_id, limit=limit, offset=offset
        )

    async def _get_city(
        self, city_id: int, uow: UnitOfWork = Depends(get_uow)
    ):
        logger.info(f"Getting city {city_id}")
        return GeoService(uow).get_city(city_id)

    async def _update_region(
        self,
        region_id: int,
        payload: RegionSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Updating region {region_id}")
        return GeoService(uow).update_region(region_id, payload)

    async def _delete_region(
        self,
        region_id: int,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Deleting region {region_id}")
        GeoService(uow).delete_region(region_id)
        return None

    async def _update_district(
        self,
        district_id: int,
        payload: DistrictSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Updating district {district_id}")
        return GeoService(uow).update_district(district_id, payload)

    async def _delete_district(
        self,
        district_id: int,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Deleting district {district_id}")
        GeoService(uow).delete_district(district_id)
        return None

    async def _update_city(
        self,
        city_id: int,
        payload: CitySchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Updating city {city_id}")
        return GeoService(uow).update_city(city_id, payload)

    async def _delete_city(
        self,
        city_id: int,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Deleting city {city_id}")
        GeoService(uow).delete_city(city_id)
        return None


geo_router = GeoRouter().router
