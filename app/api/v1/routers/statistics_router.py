from typing import List
from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_uow
from app.core.auth import auth_manager
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.services.statistics_service import DashboardStatisticsService
from app.schemas.statistics_schema import CategoryStats, BuildingAssessmentSummary, LocationStats
from app.utils.logger import get_logger

logger = get_logger("statistics_router")


class StatisticsRouter:
    """Statistics endpoints for dashboard data."""

    def __init__(self) -> None:
        self.router = APIRouter(prefix="/statistics", tags=["Statistics"])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.get("/by-category-region", response_model=List[CategoryStats])(self._get_by_category_region)
        self.router.get("/building-summaries", response_model=List[BuildingAssessmentSummary])(self._get_building_summaries)
        self.router.get("/category/{category_id}/region/{region_id}", response_model=LocationStats)(self._get_category_region_details)

    async def _get_by_category_region(
        self,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        """Get statistics grouped by category and region."""
        logger.info("Getting statistics by category and region")
        return DashboardStatisticsService(uow).get_by_category_and_region()

    async def _get_building_summaries(
        self,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        """Get building assessment summaries for classification."""
        logger.info("Getting building assessment summaries")
        return DashboardStatisticsService(uow).get_building_assessment_summaries()

    async def _get_category_region_details(
        self,
        category_id: int,
        region_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        """Get detailed statistics for a specific category and region."""
        logger.info(f"Getting statistics for category {category_id} and region {region_id}")
        return DashboardStatisticsService(uow).get_category_region_details(category_id, region_id)


# Create router instance
statistics_router = StatisticsRouter().router 