from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.api.v1.dependencies import get_uow
from app.core.auth import auth_manager
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.location_image_schema import (
    LocationImageCreate,
    LocationImageOut,
)
from app.services.image_service import ImageService
from app.utils.external_storage import MinioClient
from app.utils.logger import get_logger


logger = get_logger("image_router")


class ImageRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/images", tags=["Images"])
        self._register()

    def _register(self):
        self.router.post("/presigned")(self._get_presigned_url)
        self.router.post(
            "/presigned/metadata",
            response_model=LocationImageOut,
            summary="Register image URL + description & position",
            status_code=status.HTTP_201_CREATED,
            dependencies=[Depends(auth_manager.get_current_user)],
        )(self.post_metadata)
        self.router.delete("/{image_id}", status_code=204)(self.delete_image)

        # Add this route to get a presigned GET URL for an image
        self.router.get("/{object_key:path}")(self._get_image_url)

    async def _get_presigned_url(
        self,
        location_id: str,
        filename: str,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        # e.g., inspector role_id 4
        if current.role_id not in (1, 2, 4):
            raise HTTPException(403, "Only inspectors/admins")
        logger.info(
            f"Generating upload URL for location_id: {location_id}, filename: {filename}")
        return ImageService(uow).generate_upload_url(
            location_id, filename, current
        )

    def post_metadata(
        payload: LocationImageCreate,
        location_id: UUID,
        uow: UnitOfWork = Depends(get_uow),
        current=Depends(auth_manager.get_current_user),
    ):
        # same role check…
        if current.role_id not in (1, 2, 4):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return ImageService(uow).register_metadata(str(location_id), payload)

    def delete_image(
        self,
        image_id: int,
        uow=Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        img = uow.location_images.get(image_id)
        if not img:
            raise HTTPException(404, "Image not found")
        # Delete from MinIO storage
        minio = MinioClient()
        try:
            minio._client.remove_object(minio._bucket, img.image_url)
        except Exception as e:
            logger.warning(f"Failed to delete image from MinIO: {e}")
        uow.location_images.delete(img)
        uow.commit()
        return

    async def _get_image_url(self, object_key: str):
        """Get a presigned URL for an image by object key."""
        try:
            # Generate a presigned URL for the object
            minio = MinioClient()
            presigned_url = minio.presigned_get_url(
                object_key, expire_minutes=60
            )

            # Return a redirect to the presigned URL
            return RedirectResponse(url=presigned_url)
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to generate presigned URL"
            )


image_router = ImageRouter().router
