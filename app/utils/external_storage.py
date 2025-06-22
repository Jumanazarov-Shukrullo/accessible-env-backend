import io
from datetime import timedelta

from fastapi import UploadFile
from minio import Minio

from app.core.config import settings


class MinioClient:
    """Singleton helper for presigned uploads / downloads."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            # For Railway deployment, always use HTTPS
            secure = True
            endpoint = settings.storage.minio_endpoint

            # Remove protocol prefix if present
            if endpoint.startswith("http://"):
                endpoint = endpoint[7:]
                secure = False
            elif endpoint.startswith("https://"):
                endpoint = endpoint[8:]
                secure = True

            client = Minio(
                endpoint,
                access_key=settings.storage.minio_access_key,
                secret_key=settings.storage.minio_secret_key,
                secure=secure,
            )
            # create bucket if not exists
            found = client.bucket_exists(settings.storage.minio_bucket)
            if not found:
                client.make_bucket(settings.storage.minio_bucket)

            cls._instance = super().__new__(cls)
            cls._instance._client = client
            cls._instance._bucket = settings.storage.minio_bucket
        return cls._instance

    # ------------------------------------------------------------------
    def presigned_put_url(
        self, object_name: str, expire_minutes: int = 15
    ) -> str:
        return self._client.presigned_put_object(
            self._bucket,
            object_name,
            expires=timedelta(minutes=expire_minutes),
        )

    def presigned_get_url(
        self, object_name: str, expire_minutes: int = 60
    ) -> str:
        return self._client.presigned_get_object(
            self._bucket,
            object_name,
            expires=timedelta(minutes=expire_minutes),
        )

    def get_public_url(self, object_name: str) -> str:
        """Get direct public URL for an object when bucket is public.

        Args:
            object_name: The name/path of the object in MinIO

        Returns:
            str: Direct public URL to the object
        """
        # For public buckets, we can directly access objects without presigned
        # URLs
        endpoint = settings.storage.minio_endpoint
        bucket = settings.storage.minio_bucket

        # Handle Railway's endpoint format and remove port if it's standard
        # HTTPS port
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            base_url = endpoint
        else:
            # For Railway, remove :443 port from endpoint since it's default
            # for HTTPS
            if ":443" in endpoint:
                endpoint = endpoint.replace(":443", "")
            base_url = f"https://{endpoint}"

        return f"{base_url}/{bucket}/{object_name}"

    def upload_file(self, object_name: str, file: UploadFile) -> None:
        """Upload a file to MinIO storage.

        Args:
            object_name: The name/path of the object in MinIO
            file: The FastAPI UploadFile to upload
        """
        # Read the file content
        file_content = file.file.read()
        # Reset file pointer to beginning
        file.file.seek(0)
        # Upload to MinIO
        self._client.put_object(
            bucket_name=self._bucket,
            object_name=object_name,
            data=io.BytesIO(file_content),
            length=len(file_content),
            content_type=file.content_type,
        )

    @staticmethod
    def upload_profile_picture(user_id: str, file: UploadFile) -> str:
        """Upload profile picture to MinIO and return the public URL."""
        if not file.content_type.startswith("image/"):
            raise ValueError("File is not an image")
        client = MinioClient()

        # Generate file extension from the original filename
        file_extension = "jpg"
        if file.filename and "." in file.filename:
            file_extension = file.filename.split(".")[-1].lower()

        object_name = f"profile_pictures/{user_id}.{file_extension}"
        client.upload_file(object_name, file)

        # Return direct public URL instead of presigned URL
        return client.get_public_url(object_name)


def generate_presigned_url(
    object_key: str, method: str = "GET", expire_minutes: int = 60
) -> str:
    """Generate a presigned URL for the given object.

    Args:
        object_key: The key of the object in storage
        method: The HTTP method ('GET' or 'PUT')
        expire_minutes: How long the URL is valid for

    Returns:
        str: The presigned URL
    """
    client = MinioClient()
    if method.upper() == "PUT":
        return client.presigned_put_url(object_key, expire_minutes)
    else:
        return client.presigned_get_url(object_key, expire_minutes)


def get_public_url(object_key: str) -> str:
    """Get direct public URL for an object when bucket is public.

    Args:
        object_key: The key of the object in storage

    Returns:
        str: Direct public URL to the object
    """
    client = MinioClient()
    return client.get_public_url(object_key)
