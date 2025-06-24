from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, validator


# ============================================================================
# Core User Schemas (Authentication Table)
# ============================================================================


class UserBase(BaseModel):
    username: str
    email: EmailStr
    is_active: bool = True
    email_verified: bool = False


class UserCreate(UserBase):
    password: str
    role_id: Optional[int] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    email_verified: Optional[bool] = None
    role_id: Optional[int] = None


class UserCore(UserBase):
    user_id: str
    role_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @validator("user_id", pre=True)
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


# ============================================================================
# User Profile Schemas (Profile Table)
# ============================================================================


class UserProfileBase(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    surname: Optional[str] = None
    middle_name: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    language_preference: str = "en"

    @validator("language_preference")
    def validate_language(cls, v):
        if v not in ["en", "ru", "uz"]:
            raise ValueError("Language must be en, ru, or uz")
        return v


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    surname: Optional[str] = None
    middle_name: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    language_preference: Optional[str] = None


class UserProfile(UserProfileBase):
    user_id: str
    created_at: datetime
    updated_at: datetime

    @validator("user_id", pre=True)
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


# ============================================================================
# User Security Schemas (Security Table)
# ============================================================================


class UserSecurityBase(BaseModel):
    failed_login_attempts: int = 0
    two_factor_enabled: bool = False


class UserSecurity(UserSecurityBase):
    user_id: str
    last_login_at: Optional[datetime] = None
    password_reset_token: Optional[str] = None
    password_reset_token_expires: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    password_changed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @validator("user_id", pre=True)
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


# ============================================================================
# Combined User Response Schemas
# ============================================================================


class UserResponse(UserCore):
    """Complete user response with profile data"""

    profile: Optional[UserProfile] = None
    security: Optional[UserSecurity] = None

    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Detailed user response including role information"""

    role_name: Optional[str] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list response for admin endpoints"""

    user_id: str
    username: str
    email: str
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    surname: Optional[str] = None
    is_active: bool
    email_verified: bool
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime

    @validator("user_id", pre=True)
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


# ============================================================================
# Authentication Schemas
# ============================================================================


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    permissions: list[str] = []


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# ============================================================================
# User Management Schemas
# ============================================================================


class InviteCreate(BaseModel):
    username: str
    email: EmailStr
    role_id: int
    # Profile fields
    first_name: Optional[str] = None
    surname: Optional[str] = None
    middle_name: Optional[str] = None
    phone_number: Optional[str] = None
    language_preference: str = "en"


class UserInviteResponse(BaseModel):
    user: UserResponse
    temporary_password: str
    message: str

    class Config:
        from_attributes = True


class MinimalUserResponse(BaseModel):
    user_id: str
    username: str
    full_name: Optional[str] = None

    @validator("user_id", pre=True)
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class PaginatedMinimalUsers(BaseModel):
    users: List[MinimalUserResponse]
    total: int


class ProfilePictureResponse(BaseModel):
    url: str


class PaginatedUsers(BaseModel):
    users: List[UserListResponse]
    total: int
