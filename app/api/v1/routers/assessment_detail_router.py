from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from typing import List, Optional
from sqlalchemy import insert, select

from app.api.v1.dependencies import get_uow
from app.core.auth import auth_manager
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.models.assessment_model import AssessmentComment, LocationAssessment
from app.schemas.assessment_detail_schema import CommentSchema, DetailSchema, ImageSchema, VerificationSchema
from app.services.assessment_detail_service import AssessmentDetailService
from app.utils.logger import get_logger
from app.utils.external_storage import MinioClient

logger = get_logger("assessment_detail_router")


class AssessmentDetailRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/assessment-details", tags=["Assessment Details"])
        self._register()

    def _register(self):
        self.router.post("/images/presign", status_code=200)(self._presign_image)
        self.router.post("/images/metadata", response_model=ImageSchema.Out)(self._add_image_metadata)
        self.router.post("/", response_model=DetailSchema.Out, status_code=201)(self._add_detail)
        self.router.put("/{detail_id}", response_model=DetailSchema.Out)(self._update_detail)
        
        self.router.post("/verify", response_model=VerificationSchema.Out)(self._verify)
        self.router.post("/comments", response_model=CommentSchema.Out, status_code=201)(self._add_comment)
        
        # New endpoints for admin review
        self.router.post("/{detail_id}/admin-comment", response_model=CommentSchema.Out)(self._add_admin_comment)
        self.router.get("/{detail_id}/admin-comments", response_model=List[CommentSchema.Out])(self._get_admin_comments)
        self.router.get("/{detail_id}/images", response_model=List[ImageSchema.Out])(self._get_images)
        
        # Image deletion endpoint
        self.router.delete("/{detail_id}/images/{image_id}", status_code=204)(self._delete_image)
        
        # Direct image upload endpoint
        self.router.post("/{detail_id}/images", status_code=201)(self._upload_image_direct)

        # Mark as corrected
        self.router.post("/{detail_id}/mark_correct", response_model=DetailSchema.Out)(self._mark_correct)

    # ------------------------------------------------------------------
    async def _add_detail(
        self,
        payload: DetailSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Adding new detail")
        return AssessmentDetailService(uow).add_detail(payload, current)

    async def _update_detail(
        self,
        detail_id: int,
        payload: DetailSchema.Update,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Updating detail")
        return AssessmentDetailService(uow).update_detail(detail_id, payload, current)

    async def _presign_image(
        self,
        payload: ImageSchema.PresignRequest,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Requesting presign image upload")
        print("payload".upper(), payload)
        return AssessmentDetailService(uow).presign_image_upload(
            payload.assessment_detail_id, payload.filename, current
        )

    async def _add_image_metadata(
        self,
        payload: ImageSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Adding image metadata for assessment detail")
        return AssessmentDetailService(uow).add_image_metadata(
            payload.assessment_detail_id, payload.image_url, payload.description, current
        )

    async def _verify(
        self,
        payload: VerificationSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Verifying header")
        return AssessmentDetailService(uow).verify_header(payload, current)

    async def _add_comment(
        self,
        payload: CommentSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Adding new comment")
        return AssessmentDetailService(uow).add_comment(payload, current)
        
    async def _add_admin_comment(
        self,
        detail_id: int,
        payload: CommentSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        """Add an admin comment for a specific assessment detail"""
        logger.info(f"Adding admin comment to detail {detail_id}")
        # Check if user is admin
        if current.role_id not in (1, 2):  # Superadmin or Admin
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
            
        # Get the assessment detail to find its parent assessment ID
        detail = AssessmentDetailService(uow).get_detail(detail_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Assessment detail not found")
            
        # Create a comment with prefix indicating which criterion it's for
        criterion_prefix = f"[Criterion {detail.criterion_id}] "
        comment_text = criterion_prefix + payload.comment
        
        # Create a comment for the parent assessment using the AssessmentComment table
        comment_data = {
            "user_id": current.user_id,
            "location_set_assessment_id": detail.location_set_assessment_id,
            "comment_text": comment_text,
            "is_edited": False
        }
        
        # Add the comment to the database and get the ID
        result = uow.db.execute(
            insert(AssessmentComment)
            .values(**comment_data)
            .returning(AssessmentComment.comment_id)
        )
        comment_id = result.scalar()
        uow.commit()
        
        # Return a simple response
        return {
            "comment_id": comment_id,
            "author_id": current.user_id,
            "comment": payload.comment,        # Return the original comment without prefix
            "created_at": "2024-01-01T00:00:00",  # Placeholder - actual value doesn't matter for UI
            "is_edited": False
        }
        
    async def _get_admin_comments(
        self,
        detail_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        """Get admin comments for a specific assessment detail"""
        logger.info(f"Getting admin comments for detail {detail_id}")
        # Get the assessment detail to find its parent assessment ID
        detail = AssessmentDetailService(uow).get_detail(detail_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Assessment detail not found")
            
        # Get comments for the parent assessment
        query = (
            select(AssessmentComment)
            .where(AssessmentComment.location_set_assessment_id == detail.location_set_assessment_id)
            .order_by(AssessmentComment.created_at.desc())
        )
        result = uow.db.execute(query)
        comments = list(result.scalars().all())
        
        # Filter comments that are related to this criterion
        criterion_prefix = f"[Criterion {detail.criterion_id}] "
        filtered_comments = [c for c in comments if criterion_prefix in c.comment_text]
        
        # Format comments to match CommentSchema.Out
        formatted_comments = []
        for comment in filtered_comments:
            # Extract the actual comment without the prefix
            actual_comment = comment.comment_text.replace(criterion_prefix, "")
            
            formatted_comments.append({
                "comment_id": comment.comment_id,
                "author_id": comment.user_id,
                "comment": actual_comment,
                "created_at": comment.created_at,
                "is_edited": comment.is_edited
            })
            
        return formatted_comments

    async def _get_images(
        self,
        detail_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Getting images for detail {detail_id}")
        return AssessmentDetailService(uow).get_images(detail_id)

    async def _delete_image(
        self,
        detail_id: int,
        image_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Deleting image {image_id} for detail {detail_id}")
        return AssessmentDetailService(uow).delete_image(detail_id, image_id, current)

    async def _upload_image_direct(
        self,
        detail_id: int,
        file: UploadFile,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info(f"Uploading image for detail {detail_id}")
        return AssessmentDetailService(uow).upload_image_direct(detail_id, file, current)

    async def _mark_correct(
        self,
        detail_id: int,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        service = AssessmentDetailService(uow)
        detail = service.mark_correct(detail_id, current)
        return DetailSchema.Out.model_validate(detail)


assessment_detail_router = AssessmentDetailRouter().router
