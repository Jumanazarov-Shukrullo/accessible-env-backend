from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.api.v1.dependencies import get_uow
from app.core.auth import auth_manager
from app.core.config import settings
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.assessment_schema import (
    AccessibilityCriteriaCreate,
    AccessibilityCriteriaResponse,
    AssessmentSchema,
    AssessmentSetCreate,
    AssessmentSetResponse,
    AssessmentVerificationCreate,
    LocationAssessmentCreate,
    LocationAssessmentResponse,
    LocationSetAssessmentCreate,
    LocationSetAssessmentResponse,
    SetCriteriaCreate,
)
from app.services.assessment_detail_service import AssessmentDetailService
from app.services.assessment_service import AssessmentService
from app.utils.external_storage import MinioClient
from app.utils.logger import get_logger


logger = get_logger("assessment_router")


class AssessmentRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/assessments", tags=["Assessments"])
        self._register()

    def _register(self):
        self.router.post(
            "/",
            response_model=AssessmentSchema.Out,
            status_code=status.HTTP_201_CREATED,
        )(self._create)
        self.router.get("/", response_model=list[AssessmentSchema.Out])(
            self._list
        )
        self.router.post("/{assessment_id}/submit", status_code=204)(
            self._submit
        )
        self.router.post("/{assessment_id}/verify", status_code=204)(
            self._verify
        )
        self.router.post("/{assessment_id}/reject", status_code=204)(
            self._reject
        )
        self.router.post("/{assessment_id}/reassess", status_code=204)(
            self._reassess
        )
        self.router.delete("/{assessment_id}", status_code=204)(self._delete)
        self.router.post(
            "/criteria", response_model=AccessibilityCriteriaResponse
        )(self._create_criterion)
        self.router.get(
            "/criteria", response_model=List[AccessibilityCriteriaResponse]
        )(self._list_criteria)
        self.router.get(
            "/criteria/{criterion_id}",
            response_model=AccessibilityCriteriaResponse,
        )(self._get_criterion)
        self.router.post("/sets", response_model=AssessmentSetResponse)(
            self._create_assessment_set
        )
        self.router.get("/sets", response_model=List[AssessmentSetResponse])(
            self._list_assessment_sets
        )
        self.router.get(
            "/sets/{set_id}", response_model=AssessmentSetResponse
        )(self._get_assessment_set)
        self.router.get("/sets/{set_id}/criteria", response_model=List[dict])(
            self._get_set_criteria
        )
        self.router.post(
            "/sets/{set_id}/criteria", status_code=status.HTTP_201_CREATED
        )(self._add_criterion_to_set)

        # Add direct create endpoint that doesn't need location in URL
        self.router.post(
            "/create",
            response_model=LocationSetAssessmentResponse,
            status_code=status.HTTP_201_CREATED,
        )(self._create_location_assessment_direct)

        # Add endpoint to get locations for dropdown
        self.router.get("/available-locations", response_model=List[dict])(
            self._get_available_locations
        )

        # Connect location assessment routes to their handlers
        self.router.post(
            "/locations/{location_id}/assessments",
            response_model=LocationSetAssessmentResponse,
        )(self._create_location_assessment)
        self.router.get(
            "/locations/{location_id}/assessments", response_model=List[dict]
        )(self._list_location_assessments)

        # Add convenient endpoint for verified assessments only
        self.router.get(
            "/locations/{location_id}/verified", response_model=List[dict]
        )(self._list_verified_assessments)

        # Fix the direct assessment endpoint - add it before other
        # assessment_id endpoints
        self.router.get(
            "/{assessment_id}", response_model=LocationSetAssessmentResponse
        )(self._get_assessment)

        # Add direct access to assessment details
        self.router.get(
            "/{assessment_id}/details",
            response_model=List[LocationAssessmentResponse],
        )(self._get_assessment_details)
        # Add POST endpoint for saving assessment details
        self.router.post(
            "/{assessment_id}/details",
            response_model=LocationAssessmentResponse,
        )(self._add_assessment_detail)
        # Add endpoint for direct image upload to assessment details
        self.router.post(
            "/{assessment_id}/details/{detail_id}/images", status_code=201
        )(self._upload_assessment_image)

        # Add endpoint for updating assessment details
        self.router.put(
            "/{assessment_id}/details/{detail_id}",
            response_model=LocationAssessmentResponse,
        )(self._update_assessment_detail)

        # Add new endpoint for complete assessment data
        self.router.get("/{assessment_id}/complete", response_model=dict)(
            self._get_complete_assessment_data
        )

        # Add endpoint to fix assessments that bypassed submission workflow
        self.router.post("/{assessment_id}/fix", status_code=200)(
            self._fix_assessment
        )

        # Add endpoint to recalculate overall_score for an assessment
        self.router.post("/{assessment_id}/recalculate", status_code=200)(
            self._recalculate_assessment
        )

        # Add endpoint to fix all assessments with null scores
        self.router.post("/fix-all-null-scores", status_code=200)(
            self._fix_all_null_scores
        )

    # ------------------------------------------------------------------
    async def _create(
        self,
        payload: AssessmentSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Creating assessment")
        return AssessmentService(uow).create(payload, current)

    async def _submit(
        self,
        assessment_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Submitting assessment")
        AssessmentService(uow).submit(assessment_id, current)

    async def _verify(
        self,
        assessment_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Verifying assessment")
        AssessmentService(uow).verify(assessment_id, current)

    async def _reject(
        self,
        assessment_id: int,
        rejection_data: dict,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Rejecting assessment")
        AssessmentService(uow).reject(
            assessment_id, current, rejection_data.get("reason")
        )

    async def _reassess(
        self,
        assessment_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Reassessing assessment")
        AssessmentService(uow).reassess(assessment_id, current)

    async def _delete(
        self,
        assessment_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Deleting assessment {assessment_id}")
        AssessmentService(uow).delete(assessment_id, current)

    async def _list(
        self,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Listing all assessments")
        return AssessmentService(uow).list_assessments()

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

    async def _create_assessment_set(
        self,
        assessment_set: AssessmentSetCreate,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Creating a new assessment set")
        service = AssessmentService(uow)
        return service.create_assessment_set(assessment_set)

    async def _list_assessment_sets(
        self,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Listing all assessment sets")
        service = AssessmentService(uow)
        return service.list_assessment_sets()

    async def _get_assessment_set(
        self,
        set_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Getting details of a specific assessment set")
        service = AssessmentService(uow)
        assessment_set = service.get_assessment_set(set_id)
        if not assessment_set:
            raise HTTPException(
                status_code=404, detail="Assessment set not found"
            )
        return assessment_set

    async def _add_criterion_to_set(
        self,
        set_id: int,
        criterion_data: SetCriteriaCreate,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Adding criterion to assessment set {set_id}")
        service = AssessmentService(uow)
        service.add_criterion_to_set(set_id, criterion_data)
        return {"message": "Criterion added to set successfully"}

    async def _create_location_assessment(
        self,
        location_id: UUID,
        assessment_data: LocationSetAssessmentCreate,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Creating assessment for location {location_id}")
        service = AssessmentService(uow)
        return service.create_location_assessment(
            location_id, assessment_data, current_user
        )

    async def _list_location_assessments(
        self,
        location_id: UUID,
        status: Optional[str] = Query(
            None, description="Filter by assessment status (e.g., 'verified')"
        ),
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(
            f"Listing assessments for location {location_id} with status filter: {status}")
        service = AssessmentService(uow)
        assessments = service.list_location_assessments(location_id)

        # Filter by status if provided
        if status:
            assessments = [a for a in assessments if a.status == status]

        # Convert to response format with additional fields needed for the
        # frontend
        response_data = []
        for assessment in assessments:
            # Construct display names from available fields
            assessor_name = None
            if assessment.assessor:
                # Access profile data from normalized structure
                if assessment.assessor.profile:
                    profile = assessment.assessor.profile
                    assessor_name = (
                        f"{profile.first_name} {profile.surname}".strip()
                    )
                if not assessor_name:
                    assessor_name = (
                        assessment.assessor.username
                        or assessment.assessor.email
                    )

            verifier_name = None
            if assessment.verifier:
                # Access profile data from normalized structure
                if assessment.verifier.profile:
                    profile = assessment.verifier.profile
                    verifier_name = (
                        f"{profile.first_name} {profile.surname}".strip()
                    )
                if not verifier_name:
                    verifier_name = (
                        assessment.verifier.username
                        or assessment.verifier.email
                    )

            response_data.append(
                {
                    "assessment_id": assessment.assessment_id,
                    "location_id": assessment.location_id,
                    "set_id": assessment.set_id,
                    "assessment_set_name": (
                        assessment.assessment_set.set_name
                        if assessment.assessment_set
                        else None
                    ),
                    "overall_score": assessment.overall_score,
                    "assessor_id": assessment.assessor_id,
                    "assessor_name": assessor_name,
                    "status": assessment.status,
                    "assessed_at": assessment.assessed_at,
                    "updated_at": assessment.updated_at,
                    "submitted_at": assessment.submitted_at,
                    "verified_at": assessment.verified_at,
                    "verified_by": assessment.verifier_id,
                    "verifier_name": verifier_name,
                    "notes": assessment.notes,
                }
            )

        return response_data

    async def _list_verified_assessments(
        self,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        """Convenience endpoint to get only verified assessments for a location."""
        logger.info(f"Listing verified assessments for location {location_id}")
        # Reuse the existing logic but hardcode status to 'verified'
        return await self._list_location_assessments(
            location_id, status="verified", uow=uow, current_user=current_user
        )

    async def _get_assessment(
        self,
        assessment_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        """
        Retrieves a single assessment by its ID, including its details.
        This should return the complete assessment data including criteria and scores.
        """
        logger.info(f"Getting assessment with ID: {assessment_id}")
        service = AssessmentService(uow)
        assessment = service.get_assessment(assessment_id)
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        details = service.get_assessment_details(assessment_id)
        print(details)
        response_data = {"assessment_id": assessment.assessment_id,
                         "location_id": assessment.location_id,
                         "set_id": assessment.set_id,
                         "assessor_id": assessment.assessor_id,
                         "assessed_at": assessment.assessed_at,
                         "status": assessment.status,
                         "overall_score": assessment.overall_score,
                         "assessment_set_name": (assessment.assessment_set.set_name if assessment.assessment_set else None),
                         "notes": assessment.notes,
                         "rejection_reason": assessment.rejection_reason,
                         "updated_at": assessment.updated_at,
                         "submitted_at": assessment.submitted_at,
                         "verified_at": assessment.verified_at,
                         "verifier_id": assessment.verifier_id,
                         "location_info": ({"location_id": (assessment.location.location_id if assessment.location else None),
                                            "location_name": (assessment.location.location_name if assessment.location else None),
                                            "address": (assessment.location.address if assessment.location else None),
                                            } if assessment.location else None),
                         "details": ([{"assessment_detail_id": detail.assessment_detail_id,
                                       "criterion_id": detail.criterion_id,
                                       "score": detail.score,
                                       "condition": detail.condition,
                                       "comment": detail.comment,
                                       "admin_comments": detail.admin_comments,
                                       "criterion_name": (detail.criteria.criterion_name if detail.criteria else None),
                                       "criterion_description": (detail.criteria.description if detail.criteria else None),
                                       "max_score": (detail.criteria.max_score if detail.criteria else None),
                                       "unit": (detail.criteria.unit if detail.criteria else None),
                                       "images": ([{"image_id": img.image_id,
                                                    "image_url": f"https://{settings.storage.minio_endpoint}/{settings.storage.minio_bucket}/{img.image_url}",
                                                    "description": img.description,
                                                    } for img in detail.assessment_images] if detail.assessment_images else []),
                                       } for detail in details] if details else []),
                         }
        
        return LocationSetAssessmentResponse(**response_data)

    async def _add_assessment_detail(
        self,
        assessment_id: int,
        detail_data: LocationAssessmentCreate,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Adding detail to assessment {assessment_id}")
        service = AssessmentService(uow)
        return service.add_assessment_detail(assessment_id, detail_data)

    async def _submit_assessment(
        self,
        assessment_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Submitting assessment {assessment_id}")
        service = AssessmentService(uow)
        return service.submit_assessment(assessment_id, current_user)

    async def _verify_assessment(
        self,
        assessment_id: int,
        verification_data: AssessmentVerificationCreate,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Verifying assessment {assessment_id}")
        service = AssessmentService(uow)
        return service.verify_assessment(
            assessment_id, current_user, verification_data
        )

    async def _get_assessment_details(
        self,
        assessment_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Getting details for assessment {assessment_id}")
        service = AssessmentService(uow)
        return service.get_assessment_details(assessment_id)

    # ------------------------------------------------------------------
    # Direct location assessment creation handler
    async def _create_location_assessment_direct(
        self,
        assessment_data: LocationSetAssessmentCreate,
        location_id: UUID = Query(
            ..., description="ID of the location for this assessment"
        ),
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        assessment = AssessmentService(uow).create_location_assessment_direct(
            location_id=location_id,
            assessor_id=current_user.user_id,
            set_id=assessment_data.set_id,
            notes=assessment_data.notes,
            criterion_ids=assessment_data.criterion_ids,
        )

        # Convert SQLAlchemy model to Pydantic response model
        response_data = {
            "assessment_id": assessment.assessment_id,
            "location_id": assessment.location_id,
            "set_id": assessment.set_id,
            "assessor_id": assessment.assessor_id,
            "assessed_at": assessment.assessed_at,
            "updated_at": assessment.updated_at,
            "status": assessment.status,
            "overall_score": assessment.overall_score,
            "notes": assessment.notes,
            "verified": False,
            "verified_at": None,
            "verified_by": None,
            "location_info": (
                {
                    "location_id": (
                        assessment.location.location_id
                        if assessment.location
                        else None
                    ),
                    "location_name": (
                        assessment.location.location_name
                        if assessment.location
                        else None
                    ),
                    "address": (
                        assessment.location.address
                        if assessment.location
                        else None
                    ),
                }
                if assessment.location
                else None
            ),
            "details": [],  # Empty list since details are created but not populated yet
        }
        return LocationSetAssessmentResponse(**response_data)

    async def _get_available_locations(
        self,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Fetching available locations for assessment dropdown")
        service = AssessmentService(uow)
        return service.get_available_locations()

    # Add this new endpoint after the _get_assessment_details method
    async def _get_complete_assessment_data(
        self,
        assessment_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        """
        Retrieves complete assessment data including location details, criteria, scores, etc.
        This endpoint is designed to provide all necessary information for viewing or editing an assessment.
        """
        logger.info(
            f"Getting complete assessment data for ID: {assessment_id}"
        )
        # Re-route to the existing _get_assessment logic which aims to do the
        # same
        assessment_response_model = await self._get_assessment(
            assessment_id=assessment_id, uow=uow, current_user=current_user
        )
        return assessment_response_model.model_dump()

    async def _update_assessment_detail(
        self,
        assessment_id: int,
        detail_id: int,
        payload: dict,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        """Update an assessment detail"""
        logger.info(
            f"Updating assessment detail {detail_id} for assessment {assessment_id}")
        from app.schemas.assessment_detail_schema import DetailSchema

        # Convert dict to proper schema
        update_payload = DetailSchema.Update(**payload)
        detail_service = AssessmentDetailService(uow)
        return detail_service.update_detail(
            detail_id, update_payload, current_user
        )

    async def _upload_assessment_image(
        self,
        assessment_id: int,
        detail_id: int,
        file: UploadFile = File(...),
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        """Upload an image for an assessment detail"""
        logger.info(
            f"Uploading image for assessment {assessment_id}, detail {detail_id}")

        # Initialize services
        detail_service = AssessmentDetailService(uow)
        minio_client = MinioClient()

        # Verify that the detail exists and user has permission
        detail = detail_service.get_detail(detail_id)
        if not detail:
            raise HTTPException(
                status_code=404, detail="Assessment detail not found"
            )

        # Check if user is authorized
        assessment_service = AssessmentService(uow)
        assessment = assessment_service.get_assessment(assessment_id)
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        is_admin = current_user.role_id in (1, 2)
        is_owner = str(assessment.assessor_id) == str(current_user.user_id)

        if not is_admin and not is_owner:
            raise HTTPException(
                status_code=403, detail="Not authorized to upload images"
            )

        # Check if assessment is submitted/verified and user is not admin
        if assessment.status in ("submitted", "verified") and not is_admin:
            raise HTTPException(
                status_code=403,
                detail="Cannot upload images after assessment is submitted",
            )

        # Generate unique object key
        import uuid

        file_extension = (
            file.filename.split(".")[-1] if "." in file.filename else "jpg"
        )
        object_key = f"assessment_images/{assessment_id}/{detail_id}/{
            uuid.uuid4()}.{file_extension}"

        try:
            # Upload file to MinIO
            minio_client.upload_file(object_key, file)

            # Add image metadata to database
            image_metadata = detail_service.add_image_metadata(
                detail_id=detail_id,
                image_url=object_key,
                description=f"Image for assessment {assessment_id}, detail {detail_id}",
                user=current_user,
            )

            return {
                "message": "Image uploaded successfully",
                "image_id": image_metadata.image_id,
                "image_url": object_key,
            }

        except Exception as e:
            logger.error(f"Failed to upload image: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Failed to upload image"
            )

    async def _fix_assessment(
        self,
        assessment_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        """Fix assessment that bypassed submission workflow - recalculate score and set proper timestamps"""
        logger.info(f"Fixing assessment {assessment_id}")
        try:
            service = AssessmentService(uow)
            fixed_assessment = service.fix_assessment_score(assessment_id)
            return {
                "message": "Assessment fixed successfully",
                "assessment_id": assessment_id,
                "overall_score": fixed_assessment.overall_score,
            }
        except Exception as e:
            logger.error(f"Error fixing assessment {assessment_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to fix assessment: {str(e)}"
            )

    async def _recalculate_assessment(
        self,
        assessment_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        """Recalculate overall_score for an assessment based on current criterion scores"""
        logger.info(f"Recalculating assessment {assessment_id}")
        try:
            service = AssessmentService(uow)

            # Get the assessment first
            assessment = service.get_assessment(assessment_id)
            if not assessment:
                raise HTTPException(
                    status_code=404, detail="Assessment not found"
                )

            # Calculate overall score based on current criterion scores
            from sqlalchemy import func

            from app.models.assessment_model import (
                AccessibilityCriteria,
                LocationAssessment,
            )

            total_score = (
                uow.db.query(func.sum(LocationAssessment.score))
                .filter(
                    LocationAssessment.location_set_assessment_id
                    == assessment_id
                )
                .scalar()
                or 0
            )

            total_possible = (
                uow.db.query(func.sum(AccessibilityCriteria.max_score))
                .join(
                    LocationAssessment,
                    LocationAssessment.criterion_id
                    == AccessibilityCriteria.criterion_id,
                )
                .filter(
                    LocationAssessment.location_set_assessment_id
                    == assessment_id
                )
                .scalar()
                or 1  # Avoid division by zero
            )

            # Update assessment with calculated score
            assessment.overall_score = (
                total_score / total_possible
            ) * 10  # Scale to 0-10
            uow.commit()

            return {
                "message": "Assessment recalculated successfully",
                "assessment_id": assessment_id,
                "overall_score": assessment.overall_score,
                "total_score": total_score,
                "total_possible": total_possible,
            }
        except Exception as e:
            logger.error(
                f"Error recalculating assessment {assessment_id}: {e}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to recalculate assessment: {str(e)}",
            )

    async def _get_set_criteria(
        self,
        set_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Getting criteria for assessment set {set_id}")
        service = AssessmentService(uow)
        criteria = service.get_set_criteria(set_id)
        if not criteria:
            raise HTTPException(status_code=404, detail="Criteria not found")
        return criteria

    async def _fix_all_null_scores(
        self,
        uow: UnitOfWork = Depends(get_uow),
        current_user: User = Depends(auth_manager.get_current_user),
    ):
        """Fix all assessments that have null overall_score (admin only)"""
        logger.info(f"Fixing all null scores by user {current_user.user_id}")
        service = AssessmentService(uow)
        
        # Require admin permissions
        if current_user.role_id not in (1, 2):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        fixed_assessments = service.fix_all_null_scores()
        return {
            "message": f"Fixed {len(fixed_assessments)} assessments",
            "fixed_assessments": fixed_assessments
        }


assessment_router = AssessmentRouter().router
