from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import get_uow
from app.core.auth import auth_manager
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.assessment_schema import (
    AccessibilityCriteriaCreate,
    AccessibilityCriteriaResponse,
    AccessibilityCriteriaUpdate,
)
from app.services.assessment_service import AssessmentService
from app.utils.logger import get_logger


logger = get_logger("criteria_router")


class CriteriaRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/criteria", tags=["Criteria"])
        self._register()

    def _register(self):
        self.router.post("/", response_model=AccessibilityCriteriaResponse)(
            self._create_criterion
        )
        self.router.get(
            "/", response_model=List[AccessibilityCriteriaResponse]
        )(self._list_criteria)
        self.router.get(
            "/sets/{set_id}",
            response_model=List[AccessibilityCriteriaResponse],
        )(self._get_set_criteria)
        self.router.get(
            "/{criterion_id}", response_model=AccessibilityCriteriaResponse
        )(self._get_criterion)
        self.router.put(
            "/{criterion_id}", response_model=AccessibilityCriteriaResponse
        )(self._update_criterion)
        self.router.delete(
            "/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT
        )(self._delete_criterion)

    # ------------------------------------------------------------------
    async def _create_criterion(
        self,
        criterion: AccessibilityCriteriaCreate,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Creating a new accessibility criterion")
        service = AssessmentService(uow)
        return service.create_criterion(criterion)

    async def _list_criteria(
        self,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Listing all accessibility criteria")
        service = AssessmentService(uow)
        return service.list_criteria()

    async def _get_criterion(
        self,
        criterion_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Getting details of a specific criterion")
        service = AssessmentService(uow)
        criterion = service.get_criterion(criterion_id)
        if not criterion:
            raise HTTPException(status_code=404, detail="Criterion not found")
        return criterion

    async def _update_criterion(
        self,
        criterion_id: int,
        criterion_data: AccessibilityCriteriaUpdate,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Updating criterion with id: {criterion_id}")
        service = AssessmentService(uow)
        updated_criterion = service.update_criterion(
            criterion_id, criterion_data
        )
        if not updated_criterion:
            raise HTTPException(status_code=404, detail="Criterion not found")
        return updated_criterion

    async def _delete_criterion(
        self,
        criterion_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Deleting criterion with id: {criterion_id}")
        service = AssessmentService(uow)
        service.delete_criterion(criterion_id)
        return None

    async def _get_set_criteria(
        self,
        set_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Getting all criteria for a specific assessment set")
        service = AssessmentService(uow)
        criteria = service.get_set_criteria(set_id)
        return criteria or []


criteria_router = CriteriaRouter().router
