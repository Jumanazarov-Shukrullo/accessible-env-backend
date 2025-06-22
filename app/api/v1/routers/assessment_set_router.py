from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import get_uow
from app.core.auth import auth_manager
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.assessment_set_schema import (
    AssessmentSetResponse,
    AssessmentSetSchema,
)
from app.services.assessment_service import AssessmentService
from app.utils.logger import get_logger


logger = get_logger("assessment_set_router")


class AssessmentSetRouter:
    def __init__(self):
        self.router = APIRouter(
            prefix="/assessment-sets", tags=["Assessment Sets"]
        )
        self._register()

    def _register(self):
        self.router.get("/", response_model=list[AssessmentSetResponse])(
            self._list_sets
        )
        self.router.post("/", response_model=AssessmentSetResponse)(
            self._create_set
        )
        self.router.get("/{set_id}", response_model=AssessmentSetResponse)(
            self._get_set
        )
        self.router.put("/{set_id}", response_model=AssessmentSetResponse)(
            self._update_set
        )
        self.router.get("/{set_id}/criteria")(self._get_criteria)
        self.router.post(
            "/{set_id}/criteria", status_code=status.HTTP_201_CREATED
        )(self._add_criterion_to_set)

    # ------------------------------------------------------------------
    async def _list_sets(
        self,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Listing assessment sets")
        sets = AssessmentService(uow).list_sets()

        # Format the response to include all required fields
        formatted_sets = []
        for assessment_set in sets:
            # Format criteria with all required fields
            formatted_criteria = []
            if hasattr(assessment_set, "criteria"):
                for sc in assessment_set.criteria:
                    criterion = (
                        sc.criterion if hasattr(sc, "criterion") else None
                    )
                    formatted_criteria.append(
                        {
                            "set_id": sc.set_id,
                            "criterion_id": sc.criterion_id,
                            "sequence": sc.sequence,
                            "criterion_name": (
                                criterion.criterion_name
                                if criterion
                                else "Unknown"
                            ),
                            "code": criterion.code if criterion else "Unknown",
                            "description": (
                                criterion.description if criterion else None
                            ),
                            "max_score": (
                                criterion.max_score if criterion else 0
                            ),
                            "unit": criterion.unit if criterion else None,
                            "created_at": (
                                criterion.created_at if criterion else None
                            ),
                        }
                    )

            # Add the formatted assessment set
            formatted_sets.append(
                {
                    "set_id": assessment_set.set_id,
                    "set_name": assessment_set.set_name,
                    "description": assessment_set.description,
                    "version": assessment_set.version,
                    "is_active": assessment_set.is_active,
                    "created_at": assessment_set.created_at,
                    "criteria": formatted_criteria,
                }
            )

        return formatted_sets

    async def _create_set(
        self,
        assessment_set: AssessmentSetSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Creating new assessment set")
        return AssessmentService(uow).create_assessment_set(assessment_set)

    async def _get_set(
        self,
        set_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Getting assessment set {set_id}")
        assessment_set = AssessmentService(uow).get_set(set_id)
        if not assessment_set:
            raise HTTPException(
                status_code=404, detail="Assessment set not found"
            )
        return assessment_set

    async def _get_criteria(
        self,
        set_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Getting criteria for set {set_id}")
        criteria = AssessmentService(uow).get_set_criteria(set_id)
        return criteria or []

    async def _add_criterion_to_set(
        self,
        set_id: int,
        criterion: AssessmentSetSchema.Criterion,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Adding criterion to set {set_id}")
        return AssessmentService(uow).add_criterion_to_set(set_id, criterion)

    async def _update_set(
        self,
        set_id: int,
        assessment_set: AssessmentSetSchema.Update,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Updating assessment set {set_id}")
        updated_set = AssessmentService(uow).update_assessment_set(
            set_id, assessment_set
        )
        if not updated_set:
            raise HTTPException(
                status_code=404, detail="Assessment set not found"
            )
        return updated_set


assessment_set_router = AssessmentSetRouter().router
