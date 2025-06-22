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

    def reject(self, assessment_id: int, verifier: User, reason: str = None):
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
            assessment.verified_by = str(verifier.user_id)

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
            assessment.verified_by = None

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
                    == detail.location_assessment_id
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
        """List all assessments with proper string formatting for IDs"""
        with self.uow:
            # Use query with joins to get location and assessment set
            # information
            query = (
                select(LocationSetAssessment)
                .options(
                    joinedload(LocationSetAssessment.location),
                    joinedload(LocationSetAssessment.assessment_set),
                )
                .order_by(LocationSetAssessment.assessment_id.desc())
            )
            result = self.uow.db.execute(query)
            assessments_db = list(result.unique().scalars().all())

            # Format assessments for response
            assessments = []
            for assessment in assessments_db:
                # Create a dict with string IDs and location info
                assessment_dict = {
                    "assessment_id": assessment.assessment_id,
                    "location_id": str(assessment.location_id),
                    "set_id": assessment.set_id,
                    "overall_score": assessment.overall_score,
                    "assessor_id": str(assessment.assessor_id),
                    "status": assessment.status,
                    "notes": assessment.notes,
                    "assessed_at": assessment.assessed_at,
                    "updated_at": assessment.updated_at,
                    "submitted_at": assessment.submitted_at,
                    "verified_at": assessment.verified_at,
                    "verifier_id": (
                        str(assessment.verifier_id)
                        if assessment.verifier_id
                        else None
                    ),
                    # Add location information
                    "location_name": (
                        assessment.location.location_name
                        if assessment.location
                        else "Unknown Location"
                    ),
                    "location_address": (
                        assessment.location.address
                        if assessment.location
                        else None
                    ),
                    # Add assessment set information
                    "assessment_set_name": (
                        assessment.assessment_set.set_name
                        if assessment.assessment_set
                        else "Standard Assessment"
                    ),
                    "rejection_reason": assessment.rejection_reason,
                }
                assessments.append(assessment_dict)

            return assessments

    def get_location_assessments(self, location_id: UUID):
        with self.uow:
            return self.uow.assessments.get_by_location(str(location_id))

    def get_assessment_details(
        self, assessment_id: int
    ) -> List[LocationAssessment]:
        """Get all criterion details for an assessment"""
        # First, verify the assessment exists
        assessment = self.get_assessment(assessment_id)
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        try:
            # Use a safer query that explicitly selects only existing columns
            # and handles the case where uploaded_by might not exist
            query = text(
                """
                SELECT
                    la.assessment_detail_id,
                    la.location_set_assessment_id,
                    la.criterion_id,
                    la.score,
                    la.condition,
                    la.comment,
                    la.admin_comments,
                    la.is_reviewed,
                    la.is_corrected,
                    la.created_at,
                    la.updated_at,
                    ac.criterion_name,
                    ac.code,
                    ac.description,
                    ac.max_score,
                    ac.unit
                FROM location_assessments la
                JOIN accessibility_criteria ac ON ac.criterion_id = la.criterion_id
                WHERE la.location_set_assessment_id = :assessment_id
                ORDER BY la.criterion_id
            """
            )

            result = self.uow.db.execute(
                query, {"assessment_id": assessment_id}
            )
            rows = result.fetchall()

            # Convert to LocationAssessment objects
            details = []
            for row in rows:
                detail = LocationAssessment(
                    assessment_detail_id=row.assessment_detail_id,
                    location_set_assessment_id=row.location_set_assessment_id,
                    criterion_id=row.criterion_id,
                    score=row.score,
                    condition=row.condition,
                    comment=row.comment,
                    is_reviewed=row.is_reviewed,
                    is_corrected=(
                        row.is_corrected
                        if row.is_corrected is not None
                        else False
                    ),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )

                # Set admin_comments safely
                setattr(detail, "admin_comments", row.admin_comments)

                # Create criteria object
                criteria = AccessibilityCriteria(
                    criterion_id=row.criterion_id,
                    criterion_name=row.criterion_name,
                    code=row.code,
                    description=row.description,
                    max_score=row.max_score,
                    unit=row.unit,
                )
                detail.criteria = criteria

                # Load images separately with error handling
                try:
                    # Check if uploaded_by column exists before querying it
                    check_column_query = text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'assessment_images'
                        AND column_name = 'uploaded_by'
                    """
                    )
                    column_check = self.uow.db.execute(
                        check_column_query
                    ).fetchone()

                    if column_check:
                        # Query with uploaded_by column
                        images_query = text(
                            """
                            SELECT image_id, location_set_assessment_id, assessment_detail_id,
                                   image_url, description, uploaded_by, uploaded_at
                            FROM assessment_images
                            WHERE assessment_detail_id = :detail_id
                        """
                        )
                    else:
                        # Query without uploaded_by column
                        images_query = text(
                            """
                            SELECT image_id, location_set_assessment_id, assessment_detail_id,
                                   image_url, description, NULL as uploaded_by,
                                   CURRENT_TIMESTAMP as uploaded_at
                            FROM assessment_images
                            WHERE assessment_detail_id = :detail_id
                        """
                        )

                    images_result = self.uow.db.execute(
                        images_query,
                        {"detail_id": detail.assessment_detail_id},
                    )
                    image_rows = images_result.fetchall()

                    images = []
                    for img_row in image_rows:
                        image = AssessmentImage(
                            image_id=img_row.image_id,
                            location_set_assessment_id=img_row.location_set_assessment_id,
                            assessment_detail_id=img_row.assessment_detail_id,
                            image_url=img_row.image_url,
                            description=img_row.description,
                            uploaded_by=img_row.uploaded_by,
                            uploaded_at=img_row.uploaded_at,
                        )
                        images.append(image)

                    detail.assessment_images = images

                except Exception as img_error:
                    logger.warning(
                        f"Error loading images for detail {
                            detail.assessment_detail_id}: {img_error}")
                    detail.assessment_images = []

                details.append(detail)

            # For each detail, query comments from AssessmentComment
            for detail in details:
                try:
                    # Get comments for this criterion
                    criterion_prefix = f"[Criterion {detail.criterion_id}] "
                    comments_query = text(
                        """
                        SELECT comment_text, created_at
                        FROM assessment_comments
                        WHERE location_set_assessment_id = :assessment_id
                        AND comment_text LIKE :prefix
                        ORDER BY created_at DESC
                        LIMIT 1
                    """
                    )

                    comments_result = self.uow.db.execute(
                        comments_query,
                        {
                            "assessment_id": assessment_id,
                            "prefix": f"{criterion_prefix}%",
                        },
                    )
                    comment_row = comments_result.fetchone()

                    if comment_row:
                        # Extract the actual comment without the prefix
                        comment_text = comment_row.comment_text.replace(
                            criterion_prefix, ""
                        )
                        setattr(detail, "admin_comments", comment_text)

                except Exception as comment_error:
                    logger.warning(
                        f"Error loading comments for criterion {
                            detail.criterion_id}: {comment_error}")

            logger.info(
                f"Successfully loaded {
                    len(details)} details for assessment {assessment_id}")
            return details

        except Exception as e:
            logger.error(
                f"Error in get_assessment_details for assessment {assessment_id}: {e}")
            # Fallback to simpler query if the above fails
            try:
                simple_query = (
                    select(LocationAssessment)
                    .where(
                        LocationAssessment.location_set_assessment_id
                        == assessment_id
                    )
                    .options(joinedload(LocationAssessment.criteria))
                )
                result = self.uow.db.execute(simple_query)
                details = list(result.unique().scalars().all())

                # Set empty images list for all details in fallback mode
                for detail in details:
                    detail.assessment_images = []
                    setattr(detail, "admin_comments", None)

                logger.warning(
                    f"Used fallback query for assessment {assessment_id}, loaded {
                        len(details)} details")
                return details

            except Exception as fallback_error:
                logger.error(
                    f"Fallback query also failed for assessment {assessment_id}: {fallback_error}")
                raise HTTPException(
                    status_code=500, detail="Failed to load assessment details"
                )

    # -------------------------------- helpers -------------------------
    def _get_or_404(self, assessment_id: int) -> LocationSetAssessment:
        hdr = self.uow.assessments.get(assessment_id)
        if not hdr:
            raise HTTPException(404, "Assessment not found")
        return hdr

    def _require_admin(self, user: User):
        if user.role_id not in (1, 2):
            raise HTTPException(403, "Admin only")

    def _calculate_and_set_overall_score(self, assessment_id: int) -> float:
        """Calculate and set the overall score for an assessment"""
        # Get existing assessment details
        existing_details = (
            self.uow.db.query(LocationAssessment)
            .filter(
                LocationAssessment.location_set_assessment_id == assessment_id
            )
            .all()
        )

        if not existing_details:
            # If no details exist, set score to 0
            assessment = self._get_or_404(assessment_id)
            assessment.overall_score = 0.0
            return 0.0

        # Calculate overall score based on included criteria
        total_score = sum(detail.score for detail in existing_details)
        total_possible = 0

        for detail in existing_details:
            criterion = self.uow.db.get(
                AccessibilityCriteria, detail.criterion_id
            )
            if criterion:
                total_possible += criterion.max_score

        if total_possible == 0:
            total_possible = 1  # Avoid division by zero

        # Calculate score (0-10 scale)
        overall_score = (total_score / total_possible) * 10

        # Update assessment with calculated score
        assessment = self._get_or_404(assessment_id)
        assessment.overall_score = overall_score
        
        return overall_score

    # Criteria Management
    def create_criterion(
        self, data: AccessibilityCriteriaCreate
    ) -> AccessibilityCriteria:
        """Create a new accessibility criterion"""
        with self.uow:
            criterion = AccessibilityCriteria(
                criterion_name=data.criterion_name,
                code=data.code,
                description=data.description,
                max_score=data.max_score,
                unit=data.unit,
            )
            self.uow.db.add(criterion)
            self.uow.commit()
            # Invalidate the criteria cache
            cache.invalidate("criteria:list")
            return criterion

    def update_criterion(
        self, criterion_id: int, data
    ) -> Optional[AccessibilityCriteria]:
        """Update an existing accessibility criterion"""
        with self.uow:
            criterion = self.get_criterion(criterion_id)
            if not criterion:
                return None

            # Update only fields that are provided in the request
            update_data = data.dict(exclude_unset=True, exclude_none=True)
            for field, value in update_data.items():
                setattr(criterion, field, value)

            self.uow.db.commit()
            # Invalidate both the specific criterion and list caches
            cache.invalidate(f"criteria:{criterion_id}")
            cache.invalidate("criteria:list")
            return criterion

    def delete_criterion(self, criterion_id: int) -> bool:
        """Delete an accessibility criterion if it's not used in any assessment sets"""
        with self.uow:
            # First check if the criterion exists
            criterion = self.get_criterion(criterion_id)
            if not criterion:
                raise HTTPException(
                    status_code=404, detail="Criterion not found"
                )

            # Check if the criterion is used in any assessment sets
            query = select(SetCriteria).where(
                SetCriteria.criterion_id == criterion_id
            )
            result = self.uow.db.execute(query)
            if result.first():
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete criterion that is used in assessment sets",
                )

            # Delete the criterion
            self.uow.db.delete(criterion)
            self.uow.commit()

            # Invalidate both the specific criterion and list caches
            cache.invalidate(f"criteria:{criterion_id}")
            cache.invalidate("criteria:list")
            return True

    @cache.cacheable(
        lambda self: "criteria:list", ttl=3600
    )  # Cache for 1 hour
    def list_criteria(self) -> List[AccessibilityCriteria]:
        """List all accessibility criteria"""
        query = select(AccessibilityCriteria).order_by(
            AccessibilityCriteria.criterion_id
        )
        result = self.uow.db.execute(query)
        return list(result.scalars().all())

    @cache.cacheable(
        lambda self, criterion_id: f"criteria:{criterion_id}", ttl=3600
    )  # Cache for 1 hour
    def get_criterion(
        self, criterion_id: int
    ) -> Optional[AccessibilityCriteria]:
        """Get details of a specific criterion"""
        query = select(AccessibilityCriteria).where(
            AccessibilityCriteria.criterion_id == criterion_id
        )
        result = self.uow.db.execute(query)
        return result.scalar_one_or_none()

    # Assessment Sets Management
    def create_assessment_set(
        self, data: AssessmentSetCreate
    ) -> AssessmentSet:
        """Create a new assessment set"""
        with self.uow:
            assessment_set = AssessmentSet(
                set_name=data.set_name,
                description=data.description,
                version=data.version,
                is_active=True,
            )
            self.uow.assessment_sets.add(assessment_set)
            self.uow.commit()
            # Invalidate set list cache
            cache.invalidate("assessment_sets:list")
            return assessment_set

    def update_assessment_set(
        self, set_id: int, data: AssessmentSetSchema.Update
    ) -> AssessmentSet:
        """Update an existing assessment set"""
        with self.uow:
            assessment_set = self.get_assessment_set(set_id)
            if not assessment_set:
                raise HTTPException(
                    status_code=404, detail="Assessment set not found"
                )

            # Update fields
            assessment_set.set_name = data.set_name
            assessment_set.description = data.description
            assessment_set.version = data.version
            assessment_set.is_active = data.is_active

            self.uow.commit()
            # Invalidate both specific set cache and list cache
            cache.invalidate(f"assessment_sets:{set_id}")
            cache.invalidate("assessment_sets:list")
            return assessment_set

    @cache.cacheable(
        lambda self: "assessment_sets:list", ttl=3600
    )  # Cache for 1 hour
    def list_assessment_sets(self) -> List[AssessmentSet]:
        """List all assessment sets"""
        query = select(AssessmentSet).order_by(AssessmentSet.set_id)
        result = self.uow.db.execute(query)
        return list(result.scalars().all())

    @cache.cacheable(
        lambda self, set_id: f"assessment_sets:{set_id}", ttl=3600
    )  # Cache for 1 hour
    def get_assessment_set(self, set_id: int) -> Optional[AssessmentSet]:
        """Get details of a specific assessment set with its criteria"""
        query = (
            select(AssessmentSet)
            .options(
                joinedload(AssessmentSet.set_criteria).joinedload(
                    SetCriteria.criteria
                )
            )
            .where(AssessmentSet.set_id == set_id)
        )
        result = self.uow.db.execute(query)
        assessment_set = result.unique().scalar_one_or_none()

        if assessment_set:
            # Convert to dict for schema validation
            assessment_dict = {
                "set_id": assessment_set.set_id,
                "set_name": assessment_set.set_name,
                "description": assessment_set.description,
                "version": assessment_set.version,
                "is_active": assessment_set.is_active,
                "created_at": assessment_set.created_at,
                "criteria": [],
            }

            # Process criteria to include required fields from the criterion
            # relationship
            for set_criterion in assessment_set.set_criteria:
                criterion = set_criterion.criteria
                if criterion:
                    assessment_dict["criteria"].append(
                        {
                            "set_id": set_criterion.set_id,
                            "criterion_id": set_criterion.criterion_id,
                            "sequence": set_criterion.sequence,
                            # Add fields from the related criterion
                            "criterion_name": criterion.criterion_name,
                            "code": criterion.code,
                            "description": criterion.description,
                            "max_score": criterion.max_score,
                            "unit": criterion.unit,
                            "created_at": criterion.created_at,
                        }
                    )

            return assessment_dict

        return None

    @cache.cacheable(
        lambda self, set_id: f"assessment_sets:{set_id}:criteria", ttl=3600
    )  # Cache for 1 hour
    def get_set_criteria(self, set_id: int):
        with self.uow:
            # Check if the set exists first
            assessment_set = self.get_assessment_set(set_id)
            if not assessment_set:
                raise HTTPException(
                    status_code=404, detail="Assessment set not found"
                )

            # Get criteria with full details for the frontend
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
            result = self.uow.db.execute(query)

            criteria = []
            for set_criterion, criterion in result:
                criteria.append(
                    {
                        "criterion_id": criterion.criterion_id,
                        "criterion_name": criterion.criterion_name,
                        "code": criterion.code,
                        "description": criterion.description,
                        "max_score": criterion.max_score,
                        "unit": criterion.unit,
                        "sequence": set_criterion.sequence,
                        "set_id": set_criterion.set_id,
                        "created_at": criterion.created_at,
                    }
                )

            return criteria

    def add_criterion_to_set(
        self, set_id: int, data: SetCriteriaCreate
    ) -> SetCriteria:
        """Add a criterion to an assessment set with sequence number"""
        with self.uow:
            # Verify the set and criterion exist
            assessment_set = self.get_assessment_set(set_id)
            if not assessment_set:
                raise HTTPException(
                    status_code=404, detail="Assessment set not found"
                )

            criterion = self.get_criterion(data.criterion_id)
            if not criterion:
                raise HTTPException(
                    status_code=404, detail="Criterion not found"
                )

            # Check if this criterion is already in the set
            existing = (
                self.uow.db.query(SetCriteria)
                .filter(
                    SetCriteria.set_id == set_id,
                    SetCriteria.criterion_id == data.criterion_id,
                )
                .first()
            )

            if existing:
                # Update the sequence if it already exists
                existing.sequence = data.sequence
                self.uow.commit()
                # Invalidate the set criteria cache
                cache.invalidate(f"assessment_sets:{set_id}")
                cache.invalidate(f"assessment_sets:{set_id}:criteria")
                return existing

            # Add new criterion to set
            set_criterion = SetCriteria(
                set_id=set_id,
                criterion_id=data.criterion_id,
                sequence=data.sequence,
            )
            self.uow.db.add(set_criterion)
            self.uow.commit()
            # Invalidate the set criteria cache
            cache.invalidate(f"assessment_sets:{set_id}")
            cache.invalidate(f"assessment_sets:{set_id}:criteria")
            return set_criterion

    # Location Assessment Management
    def create_location_assessment_direct(
        self,
        location_id: UUID,
        assessor_id: UUID,
        set_id: int,
        notes: Optional[str],
        criterion_ids: Optional[List[int]] = None,
    ) -> LocationSetAssessment:
        try:
            with self.uow:
                # a) Verify the set exists
                if not self.get_assessment_set(set_id):
                    raise HTTPException(404, "Assessment set not found")

                # Check if an assessment already exists for this location and set
                existing_assessment = (
                    self.uow.db.query(LocationSetAssessment)
                    .filter(
                        LocationSetAssessment.location_id == str(location_id),
                        LocationSetAssessment.set_id == set_id,
                        LocationSetAssessment.status.in_([
                            AssessmentStatus.pending,
                            AssessmentStatus.draft,
                            AssessmentStatus.submitted
                        ])
                    )
                    .first()
                )
                
                if existing_assessment:
                    raise HTTPException(
                        400, 
                        f"An active assessment already exists for this location and assessment set. "
                        f"Assessment ID: {existing_assessment.assessment_id}"
                    )

                # b) Create header
                hdr = LocationSetAssessment(
                    location_id=str(location_id),
                    set_id=set_id,
                    assessor_id=str(assessor_id),
                    notes=notes,
                    status=AssessmentStatus.pending,
                    assessed_at=dt.utcnow(),
                )
                self.uow.db.add(hdr)
                self.uow.db.flush()  # so hdr.assessment_id is populated

                # c) Seed detail rows - only for selected criteria or all if none
                # specified
                if criterion_ids:
                    # Validate that all specified criteria exist in the set
                    set_criteria = (
                        self.uow.db.query(SetCriteria)
                        .filter(SetCriteria.set_id == set_id)
                        .all()
                    )
                    valid_criterion_ids = {sc.criterion_id for sc in set_criteria}

                    # Check if all requested criteria are valid for this set
                    invalid_criteria = set(criterion_ids) - valid_criterion_ids
                    if invalid_criteria:
                        raise HTTPException(
                            400, f"Criteria {
                                list(invalid_criteria)} are not part of assessment set {set_id}", )

                    # Create details only for selected criteria
                    selected_criteria = [
                        sc
                        for sc in set_criteria
                        if sc.criterion_id in criterion_ids
                    ]
                else:
                    # Create details for all criteria in the set (original
                    # behavior)
                    selected_criteria = (
                        self.uow.db.query(SetCriteria)
                        .filter(SetCriteria.set_id == set_id)
                        .all()
                    )

                for crit in selected_criteria:
                    detail = LocationAssessment(
                        location_set_assessment_id=hdr.assessment_id,
                        criterion_id=crit.criterion_id,
                        score=0,
                        condition=None,
                        comment=None,
                    )
                    self.uow.db.add(detail)

                self.uow.commit()
                self.uow.db.refresh(hdr)

                return hdr
        
        except IntegrityError as e:
            # Handle database constraint violations
            if "duplicate key value violates unique constraint" in str(e):
                raise HTTPException(
                    400, 
                    "Assessment creation failed due to a duplicate key constraint. "
                    "Please try again or contact support if the issue persists."
                )
            else:
                raise HTTPException(
                    400, 
                    f"Database integrity error: {str(e)}"
                )
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            # Handle other unexpected errors
            raise HTTPException(
                500, 
                f"Unexpected error creating assessment: {str(e)}"
            )

    def list_location_assessments(
        self, location_id: UUID
    ) -> List[LocationSetAssessment]:
        """Get all assessments for a specific location"""
        query = (
            select(LocationSetAssessment)
            .options(
                joinedload(LocationSetAssessment.location),
                joinedload(LocationSetAssessment.assessment_set),
                # Load assessor with profile
                joinedload(LocationSetAssessment.assessor).joinedload(
                    User.profile
                ),
                # Load verifier with profile
                joinedload(LocationSetAssessment.verifier).joinedload(
                    User.profile
                ),
            )
            .where(LocationSetAssessment.location_id == str(location_id))
            .order_by(LocationSetAssessment.assessed_at.desc())
        )

        result = self.uow.db.execute(query)
        return list(result.unique().scalars().all())

    def add_assessment_detail(
        self, assessment_id: int, data: LocationAssessmentCreate
    ) -> LocationAssessment:
        """Add a detail (criterion score) to an assessment"""
        with self.uow:
            # Verify the assessment exists
            assessment = self.get_assessment(assessment_id)
            if not assessment:
                raise HTTPException(
                    status_code=404, detail="Assessment not found"
                )

            # Verify the criterion exists
            criterion = self.get_criterion(data.criterion_id)
            if not criterion:
                raise HTTPException(
                    status_code=404, detail="Criterion not found"
                )

            # Check if criterion is in the assessment set
            set_criterion = (
                self.uow.db.query(SetCriteria)
                .filter(
                    SetCriteria.set_id == assessment.set_id,
                    SetCriteria.criterion_id == data.criterion_id,
                )
                .first()
            )

            if not set_criterion:
                raise HTTPException(
                    status_code=400, detail=f"Criterion {
                        data.criterion_id} is not part of assessment set {
                        assessment.set_id}", )

            # Check if this criterion is already scored
            existing = (
                self.uow.db.query(LocationAssessment)
                .filter(
                    LocationAssessment.location_set_assessment_id
                    == assessment_id,
                    LocationAssessment.criterion_id == data.criterion_id,
                )
                .first()
            )

            if existing:
                # Update the score if it already exists
                existing.score = data.score
                existing.condition = data.condition
                existing.comment = data.comment
                self.uow.commit()
                existing.criterion = criterion  # Attach criterion info
                return existing

            # Add new score
            detail = LocationAssessment(
                location_set_assessment_id=assessment_id,
                criterion_id=data.criterion_id,
                score=data.score,
                condition=data.condition,
                comment=data.comment,
            )
            self.uow.db.add(detail)
            self.uow.commit()

            # Attach criterion info for the response
            detail.criterion = criterion
            return detail

    def submit_assessment(self, assessment_id: int) -> LocationSetAssessment:
        """Submit an assessment for verification"""
        with self.uow:
            assessment = self.get_assessment(assessment_id)
            if not assessment:
                raise HTTPException(
                    status_code=404, detail="Assessment not found"
                )

            # Get the actual details that exist for this assessment (not all
            # criteria in the set)
            existing_details = (
                self.uow.db.query(LocationAssessment)
                .filter(
                    LocationAssessment.location_set_assessment_id
                    == assessment_id
                )
                .all()
            )

            if not existing_details:
                raise HTTPException(
                    status_code=400,
                    detail="Assessment has no criteria to submit.",
                )

            # Check that all existing criteria have been scored
            unscored_details = [d for d in existing_details if d.score == 0]
            if unscored_details:
                criterion_names = []
                for detail in unscored_details:
                    criterion = self.uow.db.get(
                        AccessibilityCriteria, detail.criterion_id
                    )
                    criterion_names.append(
                        criterion.criterion_name
                        if criterion
                        else f"Criterion {detail.criterion_id}"
                    )

                raise HTTPException(
                    status_code=400, detail=f"Assessment is incomplete. Please score: {
                        ', '.join(criterion_names)}", )

            # Check if each detail has at least one image
            details_without_images = []
            for detail in existing_details:
                image_count = (
                    self.uow.db.query(func.count(AssessmentImage.image_id))
                    .filter(
                        AssessmentImage.assessment_detail_id
                        == detail.assessment_detail_id
                    )
                    .scalar()
                )
                if image_count == 0:
                    criterion = self.uow.db.get(
                        AccessibilityCriteria, detail.criterion_id
                    )
                    criterion_name = (
                        criterion.criterion_name
                        if criterion
                        else f"Criterion {detail.criterion_id}"
                    )
                    details_without_images.append(criterion_name)

            if details_without_images:
                criteria_list = ", ".join(details_without_images)
                raise HTTPException(
                    status_code=400,
                    detail=f"Each criterion must have at least one image. Missing images for: {criteria_list}",
                )

            # Calculate overall score based on included criteria only
            total_score = sum(detail.score for detail in existing_details)
            total_possible = 0

            for detail in existing_details:
                criterion = self.uow.db.get(
                    AccessibilityCriteria, detail.criterion_id
                )
                if criterion:
                    total_possible += criterion.max_score

            if total_possible == 0:
                total_possible = 1  # Avoid division by zero

            # Update assessment status and score
            assessment.status = "submitted"
            assessment.overall_score = (
                total_score / total_possible
            ) * 10  # Scale to 0-10
            assessment.submitted_at = dt.utcnow()
            self.uow.commit()

            return assessment

    def verify_assessment(
        self,
        assessment_id: int,
        verifier_id: UUID,
        data: AssessmentVerificationCreate,
    ) -> LocationSetAssessment:
        """Verify an assessment (admin/verifier only)"""
        with self.uow:
            assessment = self.get_assessment(assessment_id)
            if not assessment:
                raise HTTPException(
                    status_code=404, detail="Assessment not found"
                )

            if assessment.status != "submitted":
                raise HTTPException(
                    status_code=400, detail=f"Cannot verify assessment with status '{
                        assessment.status}'. Assessment must be submitted.", )

            # Update embedded verification fields directly on the assessment
            assessment.verifier_id = str(verifier_id)
            assessment.is_verified = data.is_verified
            assessment.verified_comment = data.comment
            assessment.verified_at = dt.utcnow()

            # Update assessment status
            assessment.status = "verified" if data.is_verified else "rejected"

            if not data.is_verified and hasattr(data, "rejection_reason"):
                assessment.rejection_reason = getattr(data, "rejection_reason")

            self.uow.commit()

            # Update location's accessibility_score if assessment was verified
            if data.is_verified:
                from app.services.location_service import LocationService

                location_service = LocationService(self.uow)
                # Handle both string and UUID types for location_id
                location_id = assessment.location_id
                if isinstance(location_id, str):
                    location_id = UUID(location_id)
                location_service.update_accessibility_score(location_id)

            return assessment

    def get_available_locations(self) -> List[dict]:
        """Get a list of available locations for assessment creation dropdown"""
        with self.uow:
            # Use a simple query to get location_id and name for dropdown
            locations = self.uow.db.query(
                self.uow.locations.model.location_id,
                self.uow.locations.model.location_name,
            ).all()

            # Format for dropdown use
            return [
                {"id": str(loc.location_id), "name": loc.location_name}
                for loc in locations
            ]

    def fix_assessment_score(
        self, assessment_id: int
    ) -> LocationSetAssessment:
        """Fix assessment that bypassed submission workflow - recalculate score and set proper timestamps"""
        with self.uow:
            assessment = self._get_or_404(assessment_id)

            # Calculate overall score based on current criterion scores
            total_score = (
                self.uow.db.query(func.sum(LocationAssessment.score))
                .filter(
                    LocationAssessment.location_set_assessment_id
                    == assessment_id
                )
                .scalar()
                or 0
            )

            total_possible = (
                self.uow.db.query(func.sum(AccessibilityCriteria.max_score))
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

            # If the assessment is verified but missing timestamps, set them
            if assessment.status == "verified" and not assessment.verified_at:
                assessment.verified_at = dt.utcnow()

            if (
                assessment.status in ["submitted", "verified"]
                and not assessment.submitted_at
            ):
                assessment.submitted_at = dt.utcnow()

            self.uow.commit()

            # Update location's accessibility_score if this is a verified
            # assessment
            if assessment.status == "verified":
                from app.services.location_service import LocationService

                location_service = LocationService(self.uow)
                # Handle both string and UUID types for location_id
                location_id = assessment.location_id
                if isinstance(location_id, str):
                    location_id = UUID(location_id)
                location_service.update_accessibility_score(location_id)

            return assessment

    def fix_all_null_scores(self) -> List[dict]:
        """Fix all assessments that have null overall_score"""
        with self.uow:
            # Find all assessments with null overall_score
            null_score_assessments = (
                self.uow.db.query(LocationSetAssessment)
                .filter(LocationSetAssessment.overall_score.is_(None))
                .all()
            )
            
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
