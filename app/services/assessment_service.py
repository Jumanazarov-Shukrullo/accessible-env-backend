from datetime import datetime as dt
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.domain.unit_of_work import UnitOfWork
from app.models.assessment_model import (
    AccessibilityCriteria,
    AssessmentImage,
    AssessmentSet,
    AssessmentStatus,
    LocationAssessment,
    LocationSetAssessment,
    SetCriteria,
)
from app.models.user_model import User
from app.schemas.assessment_schema import (
    AccessibilityCriteriaCreate,
    AssessmentSchema,
    AssessmentVerificationCreate,
    LocationAssessmentCreate,
    SetCriteriaCreate,
)
from app.schemas.assessment_set_schema import (
    AssessmentSetCreate,
    AssessmentSetSchema,
)
from app.utils.cache import cache
from app.utils.logger import get_logger
from app.core.constants import RoleID


logger = get_logger("assessment_service")


class AssessmentService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # -------------------------------- assessment creation/submission --------
    def create(
        self, payload: AssessmentSchema.Create, assessor: User
    ) -> LocationSetAssessment:
        with self.uow:
            header = LocationSetAssessment(
                location_id=str(payload.location_id),
                set_id=payload.set_id,
                assessor_id=str(assessor.user_id),
                status=AssessmentStatus.draft,
                notes=payload.notes,
            )
            self.uow.assessments.add(header)
            self.uow.commit()
            return header

    def submit(self, assessment_id: int, user: User):
        with self.uow:
            header = self._get_or_404(assessment_id)
            # Allow admins/superadmins to submit regardless of ownership
            if header.assessor_id != str(
                user.user_id
            ) and user.role_id not in (1, 2):
                raise HTTPException(status_code=403, detail="Not owner")
            # Allow both draft and pending statuses to be submitted
            if (
                header.status != AssessmentStatus.draft
                and header.status != "pending"
            ):
                raise HTTPException(
                    400,
                    f"Only draft/pending can be submitted, current status: {header.status}",
                )
            
            # Calculate overall score before submitting
            self._calculate_and_set_overall_score(assessment_id)
            
            header.status = AssessmentStatus.submitted
            header.submitted_at = dt.utcnow()
            self.uow.commit()

    def verify(self, assessment_id: int, verifier: User):
        self._require_admin(verifier)
        with self.uow:
            header = self._get_or_404(assessment_id)
            if header.status != AssessmentStatus.submitted:
                raise HTTPException(400, "Only submitted can be verified")
            
            # Ensure overall_score is calculated before verification
            if header.overall_score is None:
                self._calculate_and_set_overall_score(assessment_id)
            
            header.status = AssessmentStatus.verified
            header.verified_at = dt.utcnow()
            header.verifier_id = str(verifier.user_id)
            self.uow.commit()

    def reject(self, assessment_id: int, verifier: User, reason: Optional[str] = None):
        """Reject an assessment"""
        logger.info(
            f"Rejecting assessment {assessment_id} by {verifier.user_id}"
        )

        with self.uow:
            assessment = self._get_or_404(assessment_id)
            self._require_admin(verifier)

            assessment.status = AssessmentStatus.rejected
            assessment.rejection_reason = reason
            assessment.verified_at = dt.utcnow()
            assessment.verifier_id = str(verifier.user_id)

            self.uow.commit()

    def reassess(self, assessment_id: int, user: User):
        """Reopen a rejected assessment for editing"""
        logger.info(
            f"Reassessing assessment {assessment_id} by {user.user_id}"
        )

        with self.uow:
            assessment = self._get_or_404(assessment_id)

            # Check if user is authorized (owner or admin)
            if assessment.assessor_id != str(
                user.user_id
            ) and user.role_id not in (1, 2):
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to reassess this assessment",
                )

            # Check if assessment is in rejected status
            if assessment.status != AssessmentStatus.rejected:
                raise HTTPException(
                    status_code=400,
                    detail="Only rejected assessments can be reassessed",
                )

            # Reset assessment to draft status
            assessment.status = AssessmentStatus.draft
            assessment.rejection_reason = None
            assessment.verified_at = None
            assessment.verifier_id = None

            # Clear admin comments from all details
            details_query = select(LocationAssessment).where(
                LocationAssessment.location_set_assessment_id == assessment_id
            )
            details = self.uow.db.execute(details_query).scalars().all()

            for detail in details:
                detail.admin_comments = None

            self.uow.commit()
            logger.info(
                f"Assessment {assessment_id} successfully reopened for editing"
            )

    def delete(self, assessment_id: int, user: User):
        """Delete an assessment (admin only)"""
        logger.info(f"Deleting assessment {assessment_id} by {user.user_id}")

        with self.uow:
            assessment = self._get_or_404(assessment_id)
            self._require_admin(user)

            # Check if assessment can be deleted
            if assessment.status == "verified" and user.role_id not in [
                1,
                2,
            ]:  # Only superadmin/admin can delete verified
                raise HTTPException(
                    status_code=403,
                    detail="Cannot delete verified assessments",
                )

            # Delete related assessment details first
            details_query = select(LocationAssessment).where(
                LocationAssessment.location_set_assessment_id == assessment_id
            )
            details = self.uow.db.execute(details_query).scalars().all()

            for detail in details:
                # Delete associated images first
                images_query = select(AssessmentImage).where(
                    AssessmentImage.assessment_detail_id
                    == detail.assessment_detail_id
                )
                images = self.uow.db.execute(images_query).scalars().all()

                for image in images:
                    # TODO: Also delete from MinIO storage if needed
                    self.uow.db.delete(image)

                # Delete the detail
                self.uow.db.delete(detail)

            # Delete the assessment itself
            self.uow.db.delete(assessment)
            self.uow.commit()
            logger.info(f"Assessment {assessment_id} deleted successfully")

    # -------------------------------- assessment sets and criteria ----------
    def list_sets(self):
        with self.uow:
            return self.uow.assessment_sets.get_all()

    def get_set(self, set_id: int):
        with self.uow:
            assessment_set = self.get_assessment_set(set_id)
            return assessment_set

    # -------------------------------- retrieve assessments ------------------
    def get_assessment(
        self, assessment_id: int
    ) -> Optional[LocationSetAssessment]:
        """Get details of a specific assessment"""
        query = (
            select(LocationSetAssessment)
            .options(
                joinedload(LocationSetAssessment.location),
                joinedload(LocationSetAssessment.assessment_set),
            )
            .where(LocationSetAssessment.assessment_id == assessment_id)
        )
        result = self.uow.db.execute(query)
        assessment = result.unique().scalar_one_or_none()

        # No need to query separate verification table since fields are
        # embedded
        return assessment

    def list_assessments(self):
        """List all assessments with basic info"""
        query = (
            select(LocationSetAssessment)
            .options(
                joinedload(LocationSetAssessment.location),
                joinedload(LocationSetAssessment.assessment_set),
            )
            .order_by(LocationSetAssessment.assessed_at.desc())
        )
        result = self.uow.db.execute(query)
        assessments = result.unique().scalars().all()

        assessment_list = []
        for assessment in assessments:
            assessment_data = {
                "assessment_id": assessment.assessment_id,
                "location_id": str(assessment.location_id),
                "location_name": (
                    assessment.location.location_name
                    if assessment.location
                    else "Unknown"
                ),
                "set_id": assessment.set_id,
                "set_name": (
                    assessment.assessment_set.set_name
                    if assessment.assessment_set
                    else "Unknown Set"
                ),
                "assessor_id": str(assessment.assessor_id),
                "status": assessment.status,
                "overall_score": assessment.overall_score,
                "assessed_at": assessment.assessed_at,
                "submitted_at": assessment.submitted_at,
                "verified_at": assessment.verified_at,
                "notes": assessment.notes,
            }
            assessment_list.append(assessment_data)

        return assessment_list

    # -------------------------------- location assessments ------------------
    def get_location_assessments(self, location_id: UUID):
        """Get all assessments for a specific location"""
        return self.uow.assessments.by_location(str(location_id))

    def get_assessment_details(
        self, assessment_id: int
    ) -> List[LocationAssessment]:
        """Get all assessment details for a specific assessment"""
        query = (
            select(LocationAssessment)
            .options(
                joinedload(LocationAssessment.criteria),
                joinedload(LocationAssessment.assessment_images),
            )
            .where(LocationAssessment.location_set_assessment_id == assessment_id)
            .order_by(LocationAssessment.assessment_detail_id)
        )
        result = self.uow.db.execute(query)
        return result.unique().scalars().all()

    # -------------------------------- helper methods -------------------------
    def _get_or_404(self, assessment_id: int) -> LocationSetAssessment:
        assessment = self.uow.assessments.get(assessment_id)
        if not assessment:
            raise HTTPException(404, "Assessment not found")
        return assessment

    def _require_admin(self, user: User):
        if user.role_id not in (RoleID.ADMIN.value, RoleID.SUPERADMIN.value):
            raise HTTPException(403, "Admin access required")

    def _calculate_and_set_overall_score(self, assessment_id: int) -> float:
        """Calculate and set the overall score for an assessment"""
        with self.uow:
            # Get all assessment details for this assessment
            details_query = select(LocationAssessment).where(
                LocationAssessment.location_set_assessment_id == assessment_id
            )
            details = self.uow.db.execute(details_query).scalars().all()
            
            if not details:
                return 0.0
            
            # Calculate average score from all details
            total_score = sum(detail.score for detail in details if detail.score is not None)
            count = len([detail for detail in details if detail.score is not None])
            
            if count == 0:
                overall_score = 0.0
            else:
                overall_score = round(total_score / count, 2)
            
            # Update the assessment with the calculated score
            assessment = self._get_or_404(assessment_id)
            assessment.overall_score = overall_score
            
            logger.info(
                f"Calculated overall score for assessment {assessment_id}: {overall_score} "
                f"(from {count} details with total {total_score})"
            )
            
            return overall_score

    # -------------------------------- criteria management --------------------
    def create_criterion(
        self, data: AccessibilityCriteriaCreate
    ) -> AccessibilityCriteria:
        """Create a new accessibility criterion"""
        logger.info(f"Creating new criterion: {data.criterion_name}")

        with self.uow:
            criterion = AccessibilityCriteria(
                criterion_name=data.criterion_name,
                description=data.description,
                code=data.code,
                max_score=data.max_score,
                unit=data.unit,
            )
            self.uow.db.add(criterion)
            self.uow.commit()
            cache.invalidate("criteria:list")  # Clear cache
            return criterion

    def update_criterion(
        self, criterion_id: int, data
    ) -> Optional[AccessibilityCriteria]:
        """Update an existing criterion"""
        logger.info(f"Updating criterion {criterion_id}")

        with self.uow:
            criterion = self.uow.db.get(AccessibilityCriteria, criterion_id)
            if not criterion:
                return None

            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(criterion, field, value)

            self.uow.commit()
            cache.invalidate("criteria:list")  # Clear cache
            cache.invalidate(f"criteria:{criterion_id}")  # Clear specific cache
            return criterion

    def delete_criterion(self, criterion_id: int) -> bool:
        """Delete a criterion"""
        logger.info(f"Deleting criterion {criterion_id}")

        with self.uow:
            criterion = self.uow.db.get(AccessibilityCriteria, criterion_id)
            if not criterion:
                return False

            # Check if criterion is used in any assessment sets
            sets_using_criterion = (
                self.uow.db.execute(
                    select(SetCriteria).where(
                        SetCriteria.criterion_id == criterion_id
                    )
                )
                .scalars()
                .all()
            )

            if sets_using_criterion:
                raise HTTPException(
                    400,
                    f"Cannot delete criterion: used in {len(sets_using_criterion)} assessment sets",
                )

            self.uow.db.delete(criterion)
            self.uow.commit()
            cache.invalidate("criteria:list")  # Clear cache
            cache.invalidate(f"criteria:{criterion_id}")  # Clear specific cache
            return True

    @cache.cacheable(
        lambda self: "criteria:list", ttl=3600
    )  # Cache for 1 hour
    def list_criteria(self) -> List[AccessibilityCriteria]:
        """List all accessibility criteria"""
        with self.uow:
            query = select(AccessibilityCriteria).order_by(
                AccessibilityCriteria.criterion_name
            )
            return self.uow.db.execute(query).scalars().all()

    @cache.cacheable(
        lambda self, criterion_id: f"criteria:{criterion_id}", ttl=3600
    )  # Cache for 1 hour
    def get_criterion(
        self, criterion_id: int
    ) -> Optional[AccessibilityCriteria]:
        """Get a specific criterion"""
        with self.uow:
            return self.uow.db.get(AccessibilityCriteria, criterion_id)

    # -------------------------------- assessment sets ------------------------
    def create_assessment_set(
        self, data: AssessmentSetCreate
    ) -> AssessmentSet:
        """Create a new assessment set"""
        logger.info(f"Creating new assessment set: {data.set_name}")

        with self.uow:
            assessment_set = AssessmentSet(
                set_name=data.set_name,
                description=data.description,
                is_active=data.is_active,
            )
            self.uow.db.add(assessment_set)
            self.uow.commit()
            cache.invalidate("assessment_sets:list")  # Clear cache
            return assessment_set

    def update_assessment_set(
        self, set_id: int, data: AssessmentSetSchema.Update
    ) -> AssessmentSet:
        """Update an existing assessment set"""
        logger.info(f"Updating assessment set {set_id}")

        with self.uow:
            assessment_set = self.uow.db.get(AssessmentSet, set_id)
            if not assessment_set:
                raise HTTPException(404, "Assessment set not found")

            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(assessment_set, field, value)

            self.uow.commit()
            cache.invalidate("assessment_sets:list")  # Clear cache
            cache.invalidate(f"assessment_sets:{set_id}")  # Clear specific cache
            return assessment_set

    @cache.cacheable(
        lambda self: "assessment_sets:list", ttl=3600
    )  # Cache for 1 hour
    def list_assessment_sets(self) -> List[AssessmentSet]:
        """List all assessment sets"""
        with self.uow:
            query = select(AssessmentSet).order_by(AssessmentSet.set_name)
            return self.uow.db.execute(query).scalars().all()

    @cache.cacheable(
        lambda self, set_id: f"assessment_sets:{set_id}", ttl=3600
    )  # Cache for 1 hour
    def get_assessment_set(self, set_id: int) -> Optional[AssessmentSet]:
        """Get a specific assessment set"""
        with self.uow:
            return self.uow.db.get(AssessmentSet, set_id)

    def delete_assessment_set(self, set_id: int) -> bool:
        """Delete an assessment set"""
        logger.info(f"Deleting assessment set {set_id}")

        with self.uow:
            assessment_set = self.uow.db.get(AssessmentSet, set_id)
            if not assessment_set:
                return False

            # Check if set is used in any assessments
            assessments_using_set = (
                self.uow.db.execute(
                    select(LocationSetAssessment).where(
                        LocationSetAssessment.set_id == set_id
                    )
                )
                .scalars()
                .all()
            )

            if assessments_using_set:
                raise HTTPException(
                    400,
                    f"Cannot delete assessment set: used in {len(assessments_using_set)} assessments",
                )

            # Delete associated criteria mappings first
            criteria_mappings = (
                self.uow.db.execute(
                    select(SetCriteria).where(SetCriteria.set_id == set_id)
                )
                .scalars()
                .all()
            )
            for mapping in criteria_mappings:
                self.uow.db.delete(mapping)

            self.uow.db.delete(assessment_set)
            self.uow.commit()
            cache.invalidate("assessment_sets:list")  # Clear cache
            cache.invalidate(f"assessment_sets:{set_id}")  # Clear specific cache
            return True

    # @cache.cacheable(
    #     lambda self, set_id: f"assessment_sets:{set_id}:criteria", ttl=3600
    # )  # Cache for 1 hour - temporarily disabled
    def get_set_criteria(self, set_id: int):
        """Get all criteria for a specific assessment set"""
        with self.uow:
            query = (
                select(SetCriteria, AccessibilityCriteria)
                .join(
                    AccessibilityCriteria,
                    SetCriteria.criterion_id
                    == AccessibilityCriteria.criterion_id,
                )
                .where(SetCriteria.set_id == set_id)
                .order_by(SetCriteria.sequence)
            )
            results = self.uow.db.execute(query).all()

            criteria_list = []
            for set_criteria, criteria in results:
                criteria_data = {
                    "criterion_id": criteria.criterion_id,
                    "criterion_name": criteria.criterion_name,
                    "description": criteria.description,
                    "code": criteria.code,
                    "max_score": criteria.max_score,
                    "unit": criteria.unit,
                    "sequence": set_criteria.sequence,
                    "created_at": criteria.created_at,
                }
                criteria_list.append(criteria_data)

            return criteria_list

    def remove_criterion_from_set(self, set_id: int, criterion_id: int) -> bool:
        """Remove a criterion from an assessment set"""
        logger.info(
            f"Removing criterion {criterion_id} from set {set_id}"
        )

        with self.uow:
            mapping = (
                self.uow.db.execute(
                    select(SetCriteria).where(
                        SetCriteria.set_id == set_id,
                        SetCriteria.criterion_id == criterion_id,
                    )
                )
                .scalar_one_or_none()
            )

            if not mapping:
                return False

            self.uow.db.delete(mapping)
            self.uow.commit()
            cache.invalidate(f"assessment_sets:{set_id}:criteria")  # Clear cache
            return True

    def add_criterion_to_set(
        self, set_id: int, data: SetCriteriaCreate
    ) -> SetCriteria:
        """Add or update a criterion in an assessment set"""
        logger.info(
            f"Adding/updating criterion {data.criterion_id} in set {set_id}"
        )

        with self.uow:
            # Check if mapping already exists
            existing = (
                self.uow.db.execute(
                    select(SetCriteria).where(
                        SetCriteria.set_id == set_id,
                        SetCriteria.criterion_id == data.criterion_id,
                    )
                )
                .scalar_one_or_none()
            )

            if existing:
                # Update existing mapping instead of throwing error
                logger.info(f"Updating existing criterion {data.criterion_id} in set {set_id}")
                existing.sequence = data.sequence or existing.sequence
                set_criteria = existing
            else:
                # Create new mapping
                logger.info(f"Creating new criterion {data.criterion_id} in set {set_id}")
                # Get next order index if no sequence provided
                if not data.sequence:
                    max_order = (
                        self.uow.db.execute(
                            select(func.max(SetCriteria.sequence)).where(
                                SetCriteria.set_id == set_id
                            )
                        )
                        .scalar()
                        or 0
                    )
                    sequence = max_order + 1
                else:
                    sequence = data.sequence

                set_criteria = SetCriteria(
                    set_id=set_id,
                    criterion_id=data.criterion_id,
                    sequence=sequence,
                )
                self.uow.db.add(set_criteria)

            self.uow.commit()
            cache.invalidate(f"assessment_sets:{set_id}:criteria")  # Clear cache
            return set_criteria

    # -------------------------------- direct assessment creation -------------
    def create_location_assessment_direct(
        self,
        location_id: UUID,
        assessor_id: UUID,
        set_id: int,
        notes: Optional[str],
        criterion_ids: Optional[List[int]] = None,
    ) -> LocationSetAssessment:
        """Create a location assessment directly with specified criteria"""
        logger.info(
            f"Creating direct assessment for location {location_id} by {assessor_id}"
        )

        with self.uow:
            # Create the main assessment
            assessment = LocationSetAssessment(
                location_id=str(location_id),
                set_id=set_id,
                assessor_id=str(assessor_id),
                status=AssessmentStatus.draft,
                notes=notes,
            )
            self.uow.db.add(assessment)
            self.uow.db.flush()  # Get the ID

            # Get criteria to include
            if criterion_ids:
                criteria_query = select(AccessibilityCriteria).where(
                    AccessibilityCriteria.criterion_id.in_(criterion_ids)
                )
            else:
                # Get all criteria from the set
                criteria_query = (
                    select(AccessibilityCriteria)
                    .join(SetCriteria)
                    .where(SetCriteria.set_id == set_id)
                    .order_by(SetCriteria.sequence)
                )

            criteria = self.uow.db.execute(criteria_query).scalars().all()

            # Create assessment details for each criterion
            for criterion in criteria:
                detail = LocationAssessment(
                    location_set_assessment_id=assessment.assessment_id,
                    criterion_id=criterion.criterion_id,
                    score=0,  # Default score instead of None
                    comment=None,  # Use 'comment' instead of 'notes'
                    # Removed is_compliant as it doesn't exist
                )
                self.uow.db.add(detail)

            self.uow.commit()
            logger.info(
                f"Created assessment {assessment.assessment_id} with {len(criteria)} criteria"
            )
            return assessment

    def list_location_assessments(
        self, location_id: UUID
    ) -> List[LocationSetAssessment]:
        """List all assessments for a specific location"""
        with self.uow:
            query = (
                select(LocationSetAssessment)
                .options(
                    joinedload(LocationSetAssessment.assessment_set),
                )
                .where(LocationSetAssessment.location_id == str(location_id))
                .order_by(LocationSetAssessment.assessed_at.desc())
            )
            return self.uow.db.execute(query).unique().scalars().all()

    def add_assessment_detail(
        self, assessment_id: int, data: LocationAssessmentCreate
    ) -> LocationAssessment:
        """Add a new assessment detail to an existing assessment"""
        logger.info(
            f"Adding assessment detail for assessment {assessment_id}, criterion {data.criterion_id}"
        )

        with self.uow:
            # Verify assessment exists and is in draft status
            assessment = self._get_or_404(assessment_id)
            if assessment.status not in [AssessmentStatus.draft, "pending"]:
                raise HTTPException(
                    400, "Can only add details to draft or pending assessments"
                )

            # Check if detail already exists for this criterion
            existing = (
                self.uow.db.execute(
                    select(LocationAssessment).where(
                        LocationAssessment.location_set_assessment_id
                        == assessment_id,
                        LocationAssessment.criterion_id == data.criterion_id,
                    )
                )
                .scalar_one_or_none()
            )

            if existing:
                # Update existing detail
                existing.score = data.score
                existing.comment = data.comment  # Use 'comment' instead of 'notes'
                existing.condition = data.condition  # Use existing field
                # Removed is_compliant and assessor_notes as they don't exist
                detail = existing
            else:
                # Create new detail
                detail = LocationAssessment(
                    location_set_assessment_id=assessment_id,
                    criterion_id=data.criterion_id,
                    score=data.score,
                    comment=data.comment,  # Use 'comment' instead of 'notes'
                    condition=data.condition,  # Use existing field
                    # Removed is_compliant and assessor_notes as they don't exist
                )
                self.uow.db.add(detail)

            self.uow.commit()
            return detail

    def submit_assessment(self, assessment_id: int) -> LocationSetAssessment:
        """Submit an assessment for review"""
        logger.info(f"Submitting assessment {assessment_id}")

        with self.uow:
            assessment = self._get_or_404(assessment_id)

            if assessment.status != AssessmentStatus.draft:
                raise HTTPException(
                    400, "Only draft assessments can be submitted"
                )

            # Check if assessment has any details
            details_count = (
                self.uow.db.execute(
                    select(func.count(LocationAssessment.assessment_detail_id)).where(
                        LocationAssessment.location_set_assessment_id
                        == assessment_id
                    )
                )
                .scalar()
                or 0
            )

            if details_count == 0:
                raise HTTPException(
                    400, "Cannot submit assessment without any details"
                )

            # Calculate overall score
            self._calculate_and_set_overall_score(assessment_id)

            # Update status
            assessment.status = AssessmentStatus.submitted
            assessment.submitted_at = dt.utcnow()

            self.uow.commit()
            logger.info(
                f"Assessment {assessment_id} submitted with score {assessment.overall_score}"
            )
            return assessment

    def verify_assessment(
        self,
        assessment_id: int,
        verifier_id: UUID,
        data: AssessmentVerificationCreate,
    ) -> LocationSetAssessment:
        """Verify a submitted assessment"""
        logger.info(
            f"Verifying assessment {assessment_id} by {verifier_id}"
        )

        with self.uow:
            assessment = self._get_or_404(assessment_id)

            if assessment.status != AssessmentStatus.submitted:
                raise HTTPException(
                    400, "Only submitted assessments can be verified"
                )

            # Update assessment
            assessment.status = AssessmentStatus.verified
            assessment.verified_at = dt.utcnow()
            assessment.verifier_id = str(verifier_id)

            # Add admin comments to individual details if provided
            if data.detail_comments:
                for detail_id, comment in data.detail_comments.items():
                    detail = self.uow.db.get(LocationAssessment, detail_id)
                    if (
                        detail
                        and detail.location_set_assessment_id == assessment_id
                    ):
                        detail.admin_comments = comment

            self.uow.commit()
            logger.info(f"Assessment {assessment_id} verified successfully")
            return assessment

    def get_available_locations(self) -> List[dict]:
        """Get locations that can have assessments"""
        with self.uow:
            # Query all locations regardless of status
            query = text("""
                SELECT location_id, location_name, address, status
                FROM locations 
                ORDER BY location_name
            """)
            result = self.uow.db.execute(query)
            # Map the database field names to what the frontend expects
            locations = []
            for row in result:
                locations.append({
                    "id": row.location_id,
                    "name": row.location_name,
                    "address": row.address,
                    "status": row.status,  # Include status so frontend can show it if needed
                    "category": None  # We can add category later if needed
                })
            return locations

    def fix_assessment_score(
        self, assessment_id: int
    ) -> LocationSetAssessment:
        """Recalculate and fix the overall score for an assessment"""
        logger.info(f"Fixing score for assessment {assessment_id}")
        
        with self.uow:
            assessment = self._get_or_404(assessment_id)
            
            # Get all assessment details
            details_query = select(LocationAssessment).where(
                LocationAssessment.location_set_assessment_id == assessment_id
            )
            details = self.uow.db.execute(details_query).scalars().all()
            
            if not details:
                logger.warning(f"No details found for assessment {assessment_id}")
                assessment.overall_score = 0.0
            else:
                # Calculate new score
                scores = [detail.score for detail in details if detail.score is not None]
                if scores:
                    new_score = round(sum(scores) / len(scores), 2)
                    assessment.overall_score = new_score
                    logger.info(f"Updated score for assessment {assessment_id}: {new_score}")
                else:
                    assessment.overall_score = 0.0
                    logger.info(f"No valid scores found, set to 0.0 for assessment {assessment_id}")
            
            self.uow.commit()
            return assessment

    def fix_all_null_scores(self) -> List[dict]:
        """Fix all assessments that have null overall_score"""
        logger.info("Starting to fix all assessments with null scores")
        
        with self.uow:
            # Find all assessments with null overall_score
            null_score_query = select(LocationSetAssessment).where(
                LocationSetAssessment.overall_score.is_(None)
            )
            null_score_assessments = self.uow.db.execute(null_score_query).scalars().all()
            
            logger.info(f"Found {len(null_score_assessments)} assessments with null scores")
            
            fixed_assessments = []
            for assessment in null_score_assessments:
                try:
                    # Calculate and set the overall score
                    score = self._calculate_and_set_overall_score(assessment.assessment_id)
                    fixed_assessments.append({
                        "assessment_id": assessment.assessment_id,
                        "status": assessment.status,
                        "new_score": score
                    })
                except Exception as e:
                    logger.warning(f"Failed to fix assessment {assessment.assessment_id}: {str(e)}")
            
            # Commit all changes
            if fixed_assessments:
                self.uow.commit()
                logger.info(f"Fixed {len(fixed_assessments)} assessments with null scores")
            
            return fixed_assessments

    def update_set_criteria(self, set_id: int, criterion_ids: List[int]) -> List[SetCriteria]:
        """Update all criteria for an assessment set (replaces existing criteria)"""
        logger.info(f"Updating criteria for assessment set {set_id}")
        
        with self.uow:
            # Remove existing criteria mappings
            existing_mappings = (
                self.uow.db.execute(
                    select(SetCriteria).where(SetCriteria.set_id == set_id)
                )
                .scalars()
                .all()
            )
            
            for mapping in existing_mappings:
                self.uow.db.delete(mapping)
            
            # Add new criteria mappings
            new_mappings = []
            for index, criterion_id in enumerate(criterion_ids):
                set_criteria = SetCriteria(
                    set_id=set_id,
                    criterion_id=criterion_id,
                    sequence=index + 1,
                )
                self.uow.db.add(set_criteria)
                new_mappings.append(set_criteria)
            
            self.uow.commit()
            cache.invalidate(f"assessment_sets:{set_id}:criteria")  # Clear cache
            logger.info(f"Updated {len(new_mappings)} criteria for set {set_id}")
            return new_mappings

    def update_criteria_bulk(self, set_id: int, criteria_data: List[dict]) -> List[SetCriteria]:
        """Update criteria for an assessment set with detailed data"""
        logger.info(f"Bulk updating criteria for assessment set {set_id}")
        
        with self.uow:
            # Remove existing criteria mappings
            existing_mappings = (
                self.uow.db.execute(
                    select(SetCriteria).where(SetCriteria.set_id == set_id)
                )
                .scalars()
                .all()
            )
            
            for mapping in existing_mappings:
                self.uow.db.delete(mapping)
            
            # Add new criteria mappings
            new_mappings = []
            for index, criterion_data in enumerate(criteria_data):
                set_criteria = SetCriteria(
                    set_id=set_id,
                    criterion_id=criterion_data.get('criterion_id'),
                    sequence=criterion_data.get('sequence', index + 1),
                )
                self.uow.db.add(set_criteria)
                new_mappings.append(set_criteria)
            
            self.uow.commit()
            cache.invalidate(f"assessment_sets:{set_id}:criteria")  # Clear cache
            logger.info(f"Updated {len(new_mappings)} criteria for set {set_id}")
            return new_mappings


