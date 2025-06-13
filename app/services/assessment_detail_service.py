import uuid as _uuid
from uuid import UUID
from sqlalchemy import update, select
from fastapi import HTTPException, status, UploadFile
import datetime as dt

from app.domain.unit_of_work import UnitOfWork
from app.models.assessment_model import (
    LocationAssessment,
    AccessibilityCriteria,
    AssessmentComment,
    AssessmentImage,
    LocationSetAssessment,
)
from app.models.user_model import User
from app.schemas.assessment_detail_schema import CommentSchema, DetailSchema, ImageSchema, VerificationSchema
from app.utils.external_storage import MinioClient
from app.utils.rabbitmq_client import RabbitMQPublisherWrapper
from app.utils.logger import get_logger
from app.utils.external_storage import generate_presigned_url

logger = get_logger("assessment_detail_service")


class AssessmentDetailService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self._minio = MinioClient()
        self._mq = RabbitMQPublisherWrapper()

    # -------------- details ------------------------------------------
    def add_detail(self, payload: DetailSchema.Create, assessor: User) -> LocationAssessment:
        """Add a new assessment detail."""
        with self.uow:
            detail = LocationAssessment(**payload.dict())
            self.uow.db.add(detail)
            self.uow.commit()
            self.uow.db.refresh(detail)
            return detail

    def update_detail(self, detail_id: int, payload: DetailSchema.Update, assessor: User):
        """Update an assessment detail."""
        with self.uow:
            detail = self.uow.db.query(LocationAssessment).filter(
                LocationAssessment.assessment_detail_id == detail_id
            ).first()
            
            if not detail:
                raise HTTPException(status_code=404, detail="Assessment detail not found")
                
            # Check if user is admin or owner of the assessment
            assessment = self.uow.db.query(LocationSetAssessment).filter(
                LocationSetAssessment.assessment_id == detail.location_set_assessment_id
            ).first()
            
            is_admin = assessor.role_id in (1, 2)  # Superadmin or Admin
            is_owner = assessment and assessment.assessor_id == str(assessor.user_id)
            
            # Check if assessment is submitted/verified
            if assessment and assessment.status in ('submitted', 'verified') and not is_admin:
                raise HTTPException(
                    status_code=403, 
                    detail="Cannot update detail after assessment is submitted"
                )
                
            # Apply updates based on user role
            update_data = payload.dict(exclude_unset=True)
            
            # Only allow admins to update admin_comments
            if 'admin_comments' in update_data and not is_admin:
                del update_data['admin_comments']
                
            # Apply remaining updates
            for field, value in update_data.items():
                setattr(detail, field, value)
                
            self.uow.commit()
            self.uow.db.refresh(detail)
            return detail

    # -------------- images -------------------------------------------
    def presign_image_upload(self, detail_id: int, filename: str, user: User):
        """Generate a pre-signed URL for image upload."""
        with self.uow:
            # Verify detail exists - use the correct field name
            detail = self.uow.db.query(LocationAssessment).filter(
                LocationAssessment.assessment_detail_id == detail_id
            ).first()
            print('detail'.upper(), detail)
            if not detail:
                raise HTTPException(status_code=404, detail="Assessment detail not found")
                
            # Check if user is admin or owner of the assessment
            assessment = self.uow.db.query(LocationSetAssessment).filter(
                LocationSetAssessment.assessment_id == detail.location_set_assessment_id
            ).first()
            
            is_admin = user.role_id in (1, 2)  # Superadmin or Admin
            is_owner = assessment and assessment.assessor_id == str(user.user_id)
            
            if not is_admin and not is_owner:
                raise HTTPException(status_code=403, detail="Not authorized to upload images")
                
            # Check if assessment is submitted/verified
            if assessment and assessment.status in ('submitted', 'verified') and not is_admin:
                raise HTTPException(
                    status_code=403, 
                    detail="Cannot upload images after assessment is submitted"
                )
            
            # Generate a unique object key
            object_key = f"assessment_images/{assessment.assessment_id}/{detail_id}/{_uuid.uuid4()}-{filename}"
            
            # Generate presigned URL
            presigned_url = generate_presigned_url(object_key, "PUT")
            
            return {
                "upload_url": presigned_url,
                "image_url": object_key
            }

    def add_image_metadata(self, detail_id: int, image_url: str, description: str, user: User) -> AssessmentImage:
        """Add metadata for an uploaded image."""
        with self.uow:
            # Verify detail exists - use the correct field name
            detail = self.uow.db.query(LocationAssessment).filter(
                LocationAssessment.assessment_detail_id == detail_id
            ).first()
            
            if not detail:
                raise HTTPException(status_code=404, detail="Assessment detail not found")
                
            # Create image metadata that matches the model definition
            # (assessment_detail_id, image_url, description, created_at)
            image = AssessmentImage(
                assessment_detail_id=detail_id,
                image_url=image_url,
                description=description
            )
            
            self.uow.db.add(image)
            self.uow.commit()
            self.uow.db.refresh(image)
            return image

    # -------------- verification -------------------------------------
    def verify_header(self, payload: VerificationSchema.Create, verifier: User) -> LocationSetAssessment:
        """Update verification fields in the assessment header."""
        with self.uow:
            # Get the assessment header
            assessment = self.uow.db.query(LocationSetAssessment).filter(
                LocationSetAssessment.assessment_id == payload.location_set_assessment_id
            ).first()
            
            if not assessment:
                raise HTTPException(status_code=404, detail="Assessment not found")
            
            # Update verification fields
            assessment.is_verified = payload.is_verified
            assessment.verifier_id = str(verifier.user_id)
            assessment.verification_comment = payload.comment
            assessment.verified_at = dt.datetime.utcnow()
            
            self.uow.commit()
            self.uow.db.refresh(assessment)
            return assessment

    # -------------- comments -----------------------------------------
    def add_comment(self, payload: CommentSchema.Create, user: User):
        """Add a comment to an assessment detail."""
        with self.uow:
            comment = AssessmentComment(
                assessment_detail_id=payload.assessment_detail_id,
                author_id=str(user.user_id),
                comment=payload.comment
            )
            self.uow.db.add(comment)
            self.uow.commit()
            self.uow.db.refresh(comment)
            return comment

    def add_admin_review(self, detail_id: int, comment: str, admin: User) -> LocationAssessment:
        """
        Add admin review comment to an assessment detail.
        """
        # Get detail
        detail = self.get_detail(detail_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Detail not found")

        # Update with admin comment
        query = (
            update(LocationAssessment)
            .values(admin_comments=comment)
            .where(LocationAssessment.assessment_detail_id == detail_id)
            .returning(LocationAssessment)
        )
        result = self.uow.db.execute(query)
        updated_detail = result.fetchone()
        self.uow.commit()

        return updated_detail

    def get_detail(self, detail_id: int) -> LocationAssessment:
        """
        Get assessment detail by ID.
        """
        query = (
            select(LocationAssessment)
            .where(LocationAssessment.assessment_detail_id == detail_id)
        )
        result = self.uow.db.execute(query)
        return result.scalar_one_or_none()

    def get_images(self, detail_id: int):
        """Get all images for a specific assessment detail"""
        query = select(AssessmentImage).where(AssessmentImage.assessment_detail_id == detail_id)
        result = self.uow.db.execute(query)
        return list(result.scalars().all())
        
    def delete_image(self, detail_id: int, image_id: int, user: User) -> None:
        """
        Delete an image from assessment detail.
        """
        with self.uow:
            # Check permissions
            detail = self.get_detail(detail_id)
            if not detail:
                raise HTTPException(status_code=404, detail="Detail not found")

            # Check if user is admin or owner of the assessment
            assessment = self.uow.db.query(LocationSetAssessment).filter(
                LocationSetAssessment.assessment_id == detail.location_set_assessment_id
            ).first()
            
            is_admin = user.role_id in (1, 2)  # Superadmin or Admin
            is_owner = assessment and assessment.assessor_id == str(user.user_id)
            
            if not is_admin and not is_owner:
                raise HTTPException(status_code=403, detail="Not authorized to delete images")

            # Check if assessment is submitted/verified and user is not admin
            if assessment and assessment.status in ('submitted', 'verified') and not is_admin:
                raise HTTPException(
                    status_code=403, 
                    detail="Cannot delete images after assessment is submitted"
                )

            # Find the image
            image = self.uow.db.query(AssessmentImage).filter(
                AssessmentImage.image_id == image_id,
                AssessmentImage.assessment_detail_id == detail_id
            ).first()
            
            if not image:
                raise HTTPException(status_code=404, detail="Image not found")

            # Delete from storage
            try:
                # Note: MinioClient doesn't have delete_file method, we need to implement it
                # For now, just skip storage deletion
                logger.info(f"Skipping storage deletion for image: {image.image_url}")
            except Exception as e:
                logger.warning(f"Failed to delete image from storage: {e}")
                # Continue with database deletion even if storage deletion fails

            # Delete from database
            self.uow.db.delete(image)
            self.uow.commit()
            logger.info(f"Successfully deleted image {image_id} from database")

    def upload_image_direct(self, detail_id: int, file: UploadFile, user: User) -> dict:
        """
        Direct image upload without presigned URLs.
        """
        with self.uow:
            # Verify detail exists
            detail = self.get_detail(detail_id)
            if not detail:
                raise HTTPException(status_code=404, detail="Assessment detail not found")
                
            # Check if user is admin or owner of the assessment
            assessment = self.uow.db.query(LocationSetAssessment).filter(
                LocationSetAssessment.assessment_id == detail.location_set_assessment_id
            ).first()
            
            is_admin = user.role_id in (1, 2)  # Superadmin or Admin
            is_owner = assessment and assessment.assessor_id == str(user.user_id)
            
            if not is_admin and not is_owner:
                raise HTTPException(status_code=403, detail="Not authorized to upload images")
                
            # Check if assessment is submitted/verified
            if assessment and assessment.status in ('submitted', 'verified') and not is_admin:
                raise HTTPException(
                    status_code=403, 
                    detail="Cannot upload images after assessment is submitted"
                )
            
            # Generate a unique object key
            file_extension = file.filename.split('.')[-1] if file.filename and '.' in file.filename else 'jpg'
            object_key = f"assessment_images/{assessment.assessment_id}/{detail_id}/{_uuid.uuid4()}.{file_extension}"
            
            try:
                # Upload file to MinIO
                self._minio.upload_file(object_key, file)
                
                # Create image metadata
                image = AssessmentImage(
                    location_set_assessment_id=assessment.assessment_id,
                    assessment_detail_id=detail_id,
                    image_url=object_key,
                    description=f"Image for assessment detail {detail_id}",
                    uploaded_by=str(user.user_id)
                )
                
                self.uow.db.add(image)
                self.uow.commit()
                self.uow.db.refresh(image)
                
                return {
                    "message": "Image uploaded successfully",
                    "image_id": image.image_id,
                    "image_url": object_key
                }
                
            except Exception as e:
                logger.error(f"Failed to upload image: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

    # -------------------- Mark as Correct ------------------
    def mark_correct(self, detail_id: int, user: User):
        """Admin/Inspector marks an assessment detail as corrected by object owner."""
        with self.uow:
            detail = self.uow.assessment_details.get(detail_id)
            if not detail:
                raise HTTPException(status_code=404, detail="Assessment detail not found")

            # Only admins or inspectors involved can mark as correct
            if user.role_id not in (1, 2, 4):
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            detail.is_corrected = True
            detail.updated_at = dt.datetime.utcnow()
            self.uow.commit()
            return detail
