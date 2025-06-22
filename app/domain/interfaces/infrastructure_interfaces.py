"""Infrastructure service interfaces to decouple domain from concrete implementations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from fastapi import UploadFile


class IEmailService(ABC):
    """Interface for email service operations."""

    @abstractmethod
    async def send_verification_email(self, email: str, token: str) -> bool:
        """Send email verification link."""

    @abstractmethod
    async def send_password_reset_email(self, email: str, token: str) -> bool:
        """Send password reset link."""

    @abstractmethod
    async def send_invitation_email(
        self, email: str, temp_password: str
    ) -> bool:
        """Send invitation email with temporary password."""


class IStorageService(ABC):
    """Interface for file storage operations."""

    @abstractmethod
    async def upload_file(
        self, file: UploadFile, bucket: str, object_name: str
    ) -> str:
        """Upload file and return access URL."""

    @abstractmethod
    async def delete_file(self, bucket: str, object_name: str) -> bool:
        """Delete file from storage."""

    @abstractmethod
    async def get_file_url(
        self, bucket: str, object_name: str
    ) -> Optional[str]:
        """Get accessible URL for file."""


class ICacheService(ABC):
    """Interface for caching operations."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""

    @abstractmethod
    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL."""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""

    @abstractmethod
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""


class ISecurityService(ABC):
    """Interface for security operations."""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash password securely."""

    @abstractmethod
    def verify_password(
        self, plain_password: str, hashed_password: str
    ) -> bool:
        """Verify password against hash."""

    @abstractmethod
    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[int] = None
    ) -> str:
        """Create JWT access token."""

    @abstractmethod
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""

    @abstractmethod
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token."""


class IMessagingService(ABC):
    """Interface for messaging/event publishing."""

    @abstractmethod
    async def publish_event(
        self, topic: str, event_data: Dict[str, Any]
    ) -> bool:
        """Publish event to messaging system."""

    @abstractmethod
    async def subscribe_to_events(self, topic: str, handler: callable) -> bool:
        """Subscribe to events from topic."""


class INotificationService(ABC):
    """Interface for notification delivery."""

    @abstractmethod
    async def send_push_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send push notification to user."""

    @abstractmethod
    async def send_email_notification(
        self, email: str, subject: str, body: str
    ) -> bool:
        """Send email notification."""

    @abstractmethod
    async def send_sms_notification(self, phone: str, message: str) -> bool:
        """Send SMS notification."""
