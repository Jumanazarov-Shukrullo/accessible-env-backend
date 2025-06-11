"""Infrastructure service interfaces to decouple domain from concrete implementations."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from fastapi import UploadFile


class IEmailService(ABC):
    """Interface for email service operations."""
    
    @abstractmethod
    async def send_verification_email(self, email: str, token: str) -> bool:
        """Send email verification link."""
        pass
    
    @abstractmethod
    async def send_password_reset_email(self, email: str, token: str) -> bool:
        """Send password reset link."""
        pass
    
    @abstractmethod
    async def send_invitation_email(self, email: str, temp_password: str) -> bool:
        """Send invitation email with temporary password."""
        pass


class IStorageService(ABC):
    """Interface for file storage operations."""
    
    @abstractmethod
    async def upload_file(self, file: UploadFile, bucket: str, object_name: str) -> str:
        """Upload file and return access URL."""
        pass
    
    @abstractmethod
    async def delete_file(self, bucket: str, object_name: str) -> bool:
        """Delete file from storage."""
        pass
    
    @abstractmethod
    async def get_file_url(self, bucket: str, object_name: str) -> Optional[str]:
        """Get accessible URL for file."""
        pass


class ICacheService(ABC):
    """Interface for caching operations."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass
    
    @abstractmethod
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        pass


class ISecurityService(ABC):
    """Interface for security operations."""
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash password securely."""
        pass
    
    @abstractmethod
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        pass
    
    @abstractmethod
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[int] = None) -> str:
        """Create JWT access token."""
        pass
    
    @abstractmethod
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        pass
    
    @abstractmethod
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token."""
        pass


class IMessagingService(ABC):
    """Interface for messaging/event publishing."""
    
    @abstractmethod
    async def publish_event(self, topic: str, event_data: Dict[str, Any]) -> bool:
        """Publish event to messaging system."""
        pass
    
    @abstractmethod
    async def subscribe_to_events(self, topic: str, handler: callable) -> bool:
        """Subscribe to events from topic."""
        pass


class INotificationService(ABC):
    """Interface for notification delivery."""
    
    @abstractmethod
    async def send_push_notification(self, user_id: str, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Send push notification to user."""
        pass
    
    @abstractmethod
    async def send_email_notification(self, email: str, subject: str, body: str) -> bool:
        """Send email notification."""
        pass
    
    @abstractmethod
    async def send_sms_notification(self, phone: str, message: str) -> bool:
        """Send SMS notification."""
        pass 