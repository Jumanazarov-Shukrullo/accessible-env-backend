from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, validator


# ============================================================================
# Notification Type and Status Enums
# ============================================================================


class NotificationTypeEnum(str, Enum):
    assessment_verified = "assessment_verified"
    assessment_rejected = "assessment_rejected"
    location_approved = "location_approved"
    location_rejected = "location_rejected"
    user_registered = "user_registered"
    password_reset = "password_reset"
    system_maintenance = "system_maintenance"


class NotificationStatusEnum(str, Enum):
    pending = "pending"
    sent = "sent"
    read = "read"
    expired = "expired"
    failed = "failed"


# ============================================================================
# Core Notification Schemas
# ============================================================================


class NotificationBase(BaseModel):
    type: NotificationTypeEnum
    subject: str
    body: str
    link: Optional[str] = None
    priority: Optional[int] = None
    expires_at: Optional[datetime] = None

    @validator("priority")
    def validate_priority(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError("Priority must be between 1 and 5")
        return v


class NotificationCreate(NotificationBase):
    user_id: str
    metadata: Optional[Dict] = None


class NotificationUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    link: Optional[str] = None
    priority: Optional[int] = None
    expires_at: Optional[datetime] = None
    status: Optional[NotificationStatusEnum] = None
    is_read: Optional[bool] = None
    metadata: Optional[Dict] = None


class NotificationResponse(NotificationBase):
    id: str
    user_id: str
    status: NotificationStatusEnum
    is_read: bool
    created_at: datetime
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    metadata: Optional[Dict] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Notification Management Schemas
# ============================================================================


class NotificationBulkCreate(BaseModel):
    """Create notifications for multiple users"""

    user_ids: List[str]
    type: NotificationTypeEnum
    subject: str
    body: str
    link: Optional[str] = None
    priority: Optional[int] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict] = None


class NotificationBulkUpdate(BaseModel):
    """Update multiple notifications"""

    notification_ids: List[str]
    status: Optional[NotificationStatusEnum] = None
    is_read: Optional[bool] = None


class NotificationMarkAsRead(BaseModel):
    """Mark notification(s) as read"""

    notification_ids: List[str]


class NotificationTemplate(BaseModel):
    """Notification template for different types"""

    type: NotificationTypeEnum
    subject_template: str
    body_template: str
    default_priority: int = 3

    class Config:
        from_attributes = True


# ============================================================================
# Notification Filters and Search
# ============================================================================


class NotificationFilter(BaseModel):
    """Notification filtering options"""

    type: Optional[NotificationTypeEnum] = None
    status: Optional[NotificationStatusEnum] = None
    is_read: Optional[bool] = None
    priority: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    expires_after: Optional[datetime] = None
    expires_before: Optional[datetime] = None


class NotificationSearch(BaseModel):
    """Notification search parameters"""

    query: Optional[str] = None  # Search in subject/body
    filters: Optional[NotificationFilter] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    limit: int = 50
    offset: int = 0

    @validator("sort_by")
    def validate_sort_by(cls, v):
        allowed_fields = [
            "created_at",
            "sent_at",
            "read_at",
            "priority",
            "subject",
        ]
        if v not in allowed_fields:
            raise ValueError(
                f'Sort field must be one of: {", ".join(allowed_fields)}'
            )
        return v

    @validator("sort_order")
    def validate_sort_order(cls, v):
        if v not in ["asc", "desc"]:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v


# ============================================================================
# Notification Statistics Schemas
# ============================================================================


class NotificationStats(BaseModel):
    """Notification statistics for user"""

    total_notifications: int
    unread_count: int
    pending_count: int
    read_count: int
    expired_count: int
    failed_count: int

    class Config:
        from_attributes = True


class NotificationTypeStats(BaseModel):
    """Statistics by notification type"""

    type: NotificationTypeEnum
    count: int
    unread_count: int
    last_sent: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Paginated Response Schemas
# ============================================================================


class PaginatedNotifications(BaseModel):
    """Paginated notification response"""

    items: List[NotificationResponse]
    total: int
    page: int
    size: int
    pages: int
    unread_count: int = 0

    class Config:
        from_attributes = True


# ============================================================================
# Notification Summary Schemas
# ============================================================================


class NotificationSummary(BaseModel):
    """Brief notification summary for UI"""

    id: str
    type: NotificationTypeEnum
    subject: str
    is_read: bool
    priority: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Lightweight notification list response"""

    notifications: List[NotificationSummary]
    stats: NotificationStats

    class Config:
        from_attributes = True
