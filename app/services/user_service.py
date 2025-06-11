"""User application service - orchestrates use cases using domain services."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.constants import RoleID
from app.domain.exceptions import (
    UserNotFound,
    UserAlreadyExists,
    InvalidCredentials,
    UserAlreadyVerified,
    InvalidVerificationToken
)
from app.domain.services.user_domain_service import UserDomainService
from app.domain.interfaces.infrastructure_interfaces import ISecurityService, IStorageService, IEmailService
from app.domain.repositories.user_repository import UserRepository
from app.models.user_model import User, UserProfile, UserSecurity
from app.models.role_model import Role
from app.schemas.user_schema import (
    UserCreate, UserResponse, InviteCreate, UserUpdate, 
    UserProfileUpdate, UserDetailResponse, UserListResponse
)
from app.utils import cache
from app.utils.logger import get_logger
from app.domain.unit_of_work import IUnitOfWork, UnitOfWork
from app.core.security import SecurityManager
from app.utils.external_storage import MinioClient

logger = get_logger("user_service")
security_manager = SecurityManager()


class UserService:
    """Application service for user operations."""

    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.repo = uow.users
        self.domain_service = UserDomainService()

    def register_user(self, user_in: UserCreate) -> Tuple[User, str]:
        """Register a new user."""
        with self.uow:
            logger.info(f"Registering user: {user_in.username}")

            # Check for existing users
            existing_username = self.repo.get_by_username(user_in.username)
            existing_email = self.repo.get_by_email(user_in.email)
            
            # Domain validation
            self.domain_service.validate_user_registration(
                user_in.username, 
                user_in.email, 
                existing_username, 
                existing_email
            )

            # Prepare user data
            user_data = user_in.dict()
            if not user_data.get("full_name"):
                user_data["full_name"] = self.domain_service.construct_full_name(
                    user_data["first_name"], 
                    user_data["surname"], 
                    user_data.get("middle_name")
                )

            # Create user
            user = self.repo.create(user_data)
            token = self._generate_verification_token(user)
            verification_link = self._get_verification_link(token)

            self.uow.commit()
        
        cache.invalidate('users:')
        logger.info(f"User registered successfully: {user.username}")
        return user, verification_link

    def verify_email(self, token: str) -> User:
        """Verify user email with token."""
        logger.info("Verifying email with token")
        
        # Verify token
        payload = security_manager.verify_token(token)
        if not payload or not payload.get("email"):
            raise InvalidVerificationToken()

        # Get user
        user = self.repo.get_by_email(payload["email"])
        if not user:
            raise UserNotFound(payload["email"])
        
        if user.email_verified:
            raise UserAlreadyVerified()
        
        # Update verification status
        user.email_verified = True
        return self.repo.update(user)

    def upsert_google_user(self, google_info: dict) -> User:
        """Create or update user from Google OAuth."""
        logger.info(f"Upserting Google user: {google_info.get('email')}")
        logger.info(f"Google user info received: {google_info}")  # Debug log
        
        email = google_info["email"]
        existing_user = self.repo.get_by_email(email)

        if existing_user:
            logger.info(f"Updating existing user: {existing_user.username}")
            # Update existing user and profile
            existing_user.email = google_info.get("email", existing_user.email)
            
            with self.uow:
                # Reload user with profile to ensure we have the latest data
                user = self.uow.db.query(User).options(
                    joinedload(User.profile)
                ).filter(User.user_id == existing_user.user_id).first()
                
                # Update or create profile
                if user.profile:
                    logger.info("Updating existing profile")
                    user.profile.first_name = google_info.get("given_name", user.profile.first_name)
                    user.profile.surname = google_info.get("family_name", user.profile.surname)
                    
                    # Only update profile picture if user doesn't have a custom one
                    # (don't overwrite uploaded pictures with Google's default)
                    google_picture = google_info.get("picture", "")
                    current_picture = user.profile.profile_picture or ""
                    
                    # Check if current picture is empty, default, or a Google avatar URL
                    # If user has uploaded a custom picture, preserve it
                    is_google_avatar = (
                        current_picture == "" or 
                        current_picture.startswith("https://lh3.googleusercontent.com") or
                        current_picture.startswith("https://googleusercontent.com") or
                        current_picture.startswith("https://bucket-production")  # Railway MinIO bucket
                    )
                    
                    if is_google_avatar and google_picture:
                        user.profile.profile_picture = google_picture
                    # Keep existing custom profile picture if it exists
                    
                    # Update full_name
                    if user.profile.first_name or user.profile.surname:
                        name_parts = []
                        if user.profile.first_name:
                            name_parts.append(user.profile.first_name)
                        if user.profile.middle_name:
                            name_parts.append(user.profile.middle_name)
                        if user.profile.surname:
                            name_parts.append(user.profile.surname)
                        user.profile.full_name = " ".join(name_parts)
                else:
                    logger.info("Creating new profile for existing user")
                    # Create profile if it doesn't exist
                    from app.models.user_model import UserProfile
                    first_name = google_info.get("given_name", "")
                    surname = google_info.get("family_name", "")
                    full_name = f"{first_name} {surname}".strip() if first_name or surname else None
                    
                    profile = UserProfile(
                        user_id=user.user_id,
                        first_name=first_name,
                        surname=surname,
                        full_name=full_name,
                        profile_picture=google_info.get("picture", ""),
                        language_preference="en"
                    )
                    self.uow.db.add(profile)
                
                self.uow.commit()
                logger.info(f"Profile updated successfully for user: {user.username}")
                return user
        else:
            logger.info("Creating new Google user")
            # Create new user with profile - use the existing create_user_with_profile method
            from app.schemas.user_schema import InviteCreate
            
            first_name = google_info.get("given_name", "")
            surname = google_info.get("family_name", "") 
            username = google_info["email"].split("@")[0]
            
            # Create InviteCreate object for consistency
            user_data = InviteCreate(
                username=username,
                email=google_info["email"],
                role_id=3,  # Default user role
                first_name=first_name,
                surname=surname,
                language_preference="en"
            )
            
            with self.uow:
                # Create user using existing method but without the permission checks
                temp_password = security_manager.generate_temp_password()
                password_hash = security_manager.get_password_hash(temp_password)

                # Create core user record
                user = User(
                    username=user_data.username,
                    email=user_data.email,
                    password_hash=password_hash,
                    role_id=user_data.role_id,
                    is_active=True,
                    email_verified=True  # Google users are pre-verified
                )
                self.uow.db.add(user)
                self.uow.db.flush()  # Get user_id

                # Create user profile
                full_name = f"{first_name} {surname}".strip() if first_name or surname else None
                profile = UserProfile(
                    user_id=user.user_id,
                    first_name=first_name,
                    surname=surname,
                    full_name=full_name,
                    profile_picture=google_info.get("picture", ""),
                    language_preference="en"
                )
                self.uow.db.add(profile)

                # Create user security record
                security = UserSecurity(
                    user_id=user.user_id,
                    failed_login_attempts=0,
                    two_factor_enabled=False
                )
                self.uow.db.add(security)

                self.uow.commit()
                
                logger.info(f"New Google user created successfully: {user.username}")
                return user

    def change_role(self, target_user_id: str, new_role: str, current_user: User) -> User:
        """Change user role with validation."""
        logger.info(f"Changing role for user_id: {target_user_id} to role: {new_role}")
        
        new_role_id = int(new_role)
        target_user = self.repo.get_by_id(target_user_id)
        if not target_user:
            raise UserNotFound(target_user_id)
        
        # Domain validation
        self.domain_service.validate_role_change(current_user, target_user, new_role_id)
        
        # Update role
        target_user.role_id = new_role_id
        return self.repo.update(target_user)

    def ban_user(self, target_user_id: str, current_user: User) -> User:
        """Ban user with validation."""
        logger.info(f"Banning user: {target_user_id}")
        
        target_user = self.repo.get_by_id(target_user_id)
        if not target_user:
            raise UserNotFound(target_user_id)
        
        # Domain validation
        self.domain_service.validate_user_ban(current_user, target_user)
        
        # Ban user
        target_user.is_active = False
        return self.repo.update(target_user)

    def unban_user(self, target_user_id: str) -> User:
        """Unban user."""
        logger.info(f"Unbanning user: {target_user_id}")
        
        target_user = self.repo.get_by_id(target_user_id)
        if not target_user:
            raise UserNotFound(target_user_id)

        target_user.is_active = True
        return self.repo.update(target_user)

    def update_profile(self, current_user: User, data: dict) -> UserResponse:
        """Update user profile data."""
        logger.info(f"Updating profile for user: {current_user.username}")
        
        with self.uow:
            # Reload user with relationships
            user = self.uow.db.query(User).options(
                joinedload(User.profile),
                joinedload(User.security),
                joinedload(User.role)
            ).filter(User.user_id == current_user.user_id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Separate core user fields from profile fields
            user_fields = {"username", "email", "is_active", "email_verified"}
            profile_fields = {"first_name", "surname", "middle_name", "full_name", "phone_number", "profile_picture", "language_preference"}
            
            # Update core user fields
            user_updates = {k: v for k, v in data.items() if k in user_fields and v is not None}
            for field, value in user_updates.items():
                setattr(user, field, value)
                
            # Handle profile updates
            profile_updates = {k: v for k, v in data.items() if k in profile_fields}
            if profile_updates:
                # Get or create profile
                if not user.profile:
                    user.profile = UserProfile(user_id=user.user_id, language_preference="en")
                    self.uow.db.add(user.profile)
                    self.uow.db.flush()
                
                # Update profile fields
                for field, value in profile_updates.items():
                    if hasattr(user.profile, field):
                        setattr(user.profile, field, value)
                
                # Auto-update full_name if first_name or surname changed
                if "first_name" in profile_updates or "surname" in profile_updates:
                    name_parts = []
                    if user.profile.first_name:
                        name_parts.append(user.profile.first_name)
                    if user.profile.middle_name:
                        name_parts.append(user.profile.middle_name)
                    if user.profile.surname:
                        name_parts.append(user.profile.surname)
                    user.profile.full_name = " ".join(name_parts) if name_parts else None
            
            self.uow.commit()
            
            # Return updated user response
            return self.get_user_response(user)

    def update_profile_picture(self, current_user: User, file: UploadFile) -> str:
        """Update user profile picture."""
        logger.info(f"Updating profile picture for user: {current_user.username}")
        
        with self.uow:
            # Reload user with profile relationship
            user = self.uow.db.query(User).options(
                joinedload(User.profile)
            ).filter(User.user_id == current_user.user_id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Validate file
            if not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            if file.size > 5 * 1024 * 1024:  # 5MB limit
                raise HTTPException(status_code=400, detail="File size must be less than 5MB")
            
            # Get or create profile
            if not user.profile:
                user.profile = UserProfile(user_id=user.user_id, language_preference="en")
                self.uow.db.add(user.profile)
                self.uow.db.flush()
            
            try:
                # Upload to MinIO and get public URL
                profile_picture_url = MinioClient.upload_profile_picture(user.user_id, file)
                
                # Update profile with new picture URL
                user.profile.profile_picture = profile_picture_url
                self.uow.commit()
                
                logger.info(f"Profile picture updated for user {user.username}: {profile_picture_url}")
                return profile_picture_url
                
            except Exception as e:
                logger.error(f"Failed to upload profile picture for user {user.username}: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to upload profile picture")

    def change_password(self, current_user: User, old_password: str, new_password: str) -> None:
        """Change user password."""
        logger.info(f"Changing password for user: {current_user.username}")
        
        # Verify old password
        if not security_manager.verify_password(old_password, current_user.password_hash):
            raise InvalidCredentials()
        
        # Validate new password
        self.domain_service.validate_password_strength(new_password)
        
        # Update password
        current_user.password_hash = security_manager.hash_password(new_password)
        self.repo.update(current_user)

    def create_user_with_profile(self, user_in: InviteCreate, created_by: User) -> Tuple[User, str]:
        """Create user with profile and security tables"""
        with self.uow:
            # Check if email/username already exists
            existing_user = self.uow.db.query(User).filter(
                or_(User.email == user_in.email, User.username == user_in.username)
            ).first()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email or username already exists"
        )

        # Generate temporary password
            temp_password = security_manager.generate_temp_password()
            password_hash = security_manager.get_password_hash(temp_password)

            # Create core user record
            user = User(
                username=user_in.username,
                email=user_in.email,
                password_hash=password_hash,
                role_id=user_in.role_id,
                is_active=True,
                email_verified=False
            )
            self.uow.db.add(user)
            self.uow.db.flush()  # Get user_id

            # Create user profile
            profile = UserProfile(
                user_id=user.user_id,
                first_name=user_in.first_name,
                surname=user_in.surname,
                middle_name=user_in.middle_name,
                full_name=f"{user_in.first_name or ''} {user_in.surname or ''}".strip() or None,
                phone_number=user_in.phone_number,
                language_preference=user_in.language_preference
            )
            self.uow.db.add(profile)

            # Create user security record
            security = UserSecurity(
                user_id=user.user_id,
                failed_login_attempts=0,
                two_factor_enabled=False
            )
            self.uow.db.add(security)

            self.uow.commit()
            
            logger.info(f"User {user.username} created successfully by {created_by.username}")
            return user, temp_password

    def create_user_with_role(self, user_in: InviteCreate, created_by: User) -> Tuple[User, str]:
        """Create user with specific role - alias for create_user_with_profile method."""
        return self.create_user_with_profile(user_in, created_by)

    def get_user_with_profile(self, user_id: str) -> Optional[UserResponse]:
        """Get user with profile and security data"""
        user = self.uow.db.query(User).options(
            joinedload(User.profile),
            joinedload(User.security),
            joinedload(User.role)
        ).filter(User.user_id == user_id).first()
        
        if not user:
            return None
            
        return self.get_user_response(user)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email with all relationships"""
        return self.uow.db.query(User).options(
            joinedload(User.profile),
            joinedload(User.security),
            joinedload(User.role)
        ).filter(User.email == email).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username with all relationships"""
        return self.uow.db.query(User).options(
            joinedload(User.profile),
            joinedload(User.security),
            joinedload(User.role)
        ).filter(User.username == username).first()

    def update_user_core(self, user_id: str, user_update: UserUpdate) -> UserResponse:
        """Update core user data"""
        with self.uow:
            user = self.uow.db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Update core user fields
            for field, value in user_update.dict(exclude_unset=True).items():
                if hasattr(user, field) and value is not None:
                    setattr(user, field, value)

            self.uow.commit()
            return self.get_user_with_profile(user_id)

    def update_user_profile(self, user_id: str, profile_update: UserProfileUpdate) -> UserResponse:
        """Update user profile data"""
        with self.uow:
            profile = self.uow.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if not profile:
                # Create profile if it doesn't exist
                profile = UserProfile(user_id=user_id)
                self.uow.db.add(profile)

            # Update profile fields
            for field, value in profile_update.dict(exclude_unset=True).items():
                if hasattr(profile, field):
                    setattr(profile, field, value)

            # Update full_name if first_name or surname changed
            if profile_update.first_name is not None or profile_update.surname is not None:
                first_name = profile_update.first_name or profile.first_name or ""
                surname = profile_update.surname or profile.surname or ""
                profile.full_name = f"{first_name} {surname}".strip() or None

            self.uow.commit()
            return self.get_user_with_profile(user_id)

    def authenticate_user(self, email: str, password: str, ip_address: str = None) -> Optional[User]:
        """Authenticate user and update security info"""
        with self.uow:
            user = self.get_user_by_email(email)
            if not user:
                return None

            security = user.security
            
            # Check if account is locked due to failed attempts
            if security and security.failed_login_attempts >= 5:
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account locked due to too many failed login attempts"
                )

            # Verify password
            if not security_manager.verify_password(password, user.password_hash):
                # Update failed login attempts
                if security:
                    security.failed_login_attempts += 1
                    self.uow.commit()
                return None

            # Successful login - reset failed attempts and update login info
            if security:
                security.failed_login_attempts = 0
                security.last_login_at = self.uow.db.execute("SELECT NOW()").scalar()
                security.last_login_ip = ip_address
                self.uow.commit()

            return user

    def get_users_paginated(self, page: int = 1, size: int = 50, search: str = None, role_id: int = None) -> Tuple[List[UserListResponse], int]:
        """Get paginated list of users with search and filtering"""
        query = self.uow.db.query(User).options(
            joinedload(User.profile),
            joinedload(User.security),
            joinedload(User.role)
        )

        # Apply filters
        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                UserProfile.first_name.ilike(f"%{search}%"),
                UserProfile.surname.ilike(f"%{search}%"),
                UserProfile.full_name.ilike(f"%{search}%")
            )
            query = query.join(UserProfile, UserProfile.user_id == User.user_id, isouter=True).filter(search_filter)

        if role_id:
            query = query.filter(User.role_id == role_id)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        users = query.offset(offset).limit(size).all()

        # Convert to response format
        user_responses = []
        for user in users:
            user_data = {
                "user_id": str(user.user_id),  # Convert UUID to string
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "email_verified": user.email_verified,
                "role_id": user.role_id,
                "role_name": user.role.role_name if user.role else None,
                "created_at": user.created_at,
                "full_name": user.profile.full_name if user.profile else None,
                "first_name": user.profile.first_name if user.profile else None,
                "surname": user.profile.surname if user.profile else None,
                "last_login_at": user.security.last_login_at if user.security else None
            }
            user_responses.append(UserListResponse(**user_data))

        return user_responses, total

    def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password with verification"""
        with self.uow:
            user = self.uow.db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Verify current password
            if not security_manager.verify_password(current_password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )

            # Update password
            user.password_hash = security_manager.get_password_hash(new_password)
            
            # Update security info
            if user.security:
                user.security.password_changed_at = self.uow.db.execute("SELECT NOW()").scalar()

            self.uow.commit()
            return True

    def deactivate_user(self, user_id: str, deactivated_by: User) -> bool:
        """Deactivate user account"""
        with self.uow:
            user = self.uow.db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            user.is_active = False
            self.uow.commit()
            
            logger.info(f"User {user.username} deactivated by {deactivated_by.username}")
            return True

    def activate_user(self, user_id: str, activated_by: User) -> bool:
        """Activate user account"""
        with self.uow:
            user = self.uow.db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            user.is_active = True
            self.uow.commit()
            
            logger.info(f"User {user.username} activated by {activated_by.username}")
            return True

    def delete_user(self, user_id: str, deleted_by: User) -> bool:
        """Delete user and all related data (cascading)"""
        with self.uow:
            user = self.uow.db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            username = user.username
            self.uow.db.delete(user)  # Cascade will handle profile and security
            self.uow.commit()
            
            logger.info(f"User {username} deleted by {deleted_by.username}")
            return True

    # Repository delegation methods
    def list_users(self) -> List[User]:
        """List all users."""
        logger.info("Listing all users")
        return self.repo.get_all()

    def get_user_basic_info(self, user_id: str):
        """Get basic user information."""
        fields = ["user_id", "username", "first_name", "surname", "email", "role_id"]
        users = self.repo.get_specific_fields(fields, limit=1, offset=0)
        return users[0] if users else None

    def get_user_profile(self, user: User) -> dict:
        """Get user profile data."""
        # Always reload user with relationships to ensure complete data
        user_with_relationships = self.uow.db.query(User).options(
            joinedload(User.profile),
            joinedload(User.security),
            joinedload(User.role)
        ).filter(User.user_id == user.user_id).first()
        
        if not user_with_relationships:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get profile data
        profile = user_with_relationships.profile
        security = user_with_relationships.security
        
        # Construct full_name dynamically
        full_name = None
        if profile and (profile.first_name or profile.surname):
            name_parts = []
            if profile.first_name:
                name_parts.append(profile.first_name)
            if profile.middle_name:
                name_parts.append(profile.middle_name)
            if profile.surname:
                name_parts.append(profile.surname)
            full_name = " ".join(name_parts) if name_parts else None
        
        return {
            "user_id": str(user_with_relationships.user_id),  # Convert UUID to string
            "username": user_with_relationships.username,
            "email": user_with_relationships.email,
            "role_id": user_with_relationships.role_id,
            "is_active": user_with_relationships.is_active,
            "email_verified": user_with_relationships.email_verified,
            "created_at": user_with_relationships.created_at,
            "updated_at": user_with_relationships.updated_at,
            # Profile data as nested object
            "profile": {
                "user_id": str(user_with_relationships.user_id),
                "full_name": profile.full_name if profile else full_name,
                "first_name": profile.first_name if profile else None,
                "surname": profile.surname if profile else None,
                "middle_name": profile.middle_name if profile else None,
                "phone_number": profile.phone_number if profile else None,
                "profile_picture": profile.profile_picture if profile else None,
                "language_preference": profile.language_preference if profile else "en",
                "created_at": profile.created_at if profile else user_with_relationships.created_at,
                "updated_at": profile.updated_at if profile else user_with_relationships.updated_at,
            } if profile else None,
            # Security data as nested object
            "security": {
                "user_id": str(user_with_relationships.user_id),
                "last_login_at": security.last_login_at if security else None,
                "failed_login_attempts": security.failed_login_attempts if security else 0,
                "password_reset_token": None,  # Never expose this
                "password_reset_token_expires": None,  # Never expose this
                "two_factor_enabled": security.two_factor_enabled if security else False,
                "last_login_ip": security.last_login_ip if security else None,
                "password_changed_at": security.password_changed_at if security else None,
                "created_at": security.created_at if security else user_with_relationships.created_at,
                "updated_at": security.updated_at if security else user_with_relationships.updated_at,
            } if security else None
        }

    def get_user_response(self, user: User) -> UserResponse:
        """Convert user model to response schema"""
        if not user:
            return None
            
        # Create UserProfile object if profile exists
        profile_obj = None
        if user.profile:
            profile_data = {
                "user_id": str(user.user_id),
                "full_name": user.profile.full_name,
                "first_name": user.profile.first_name,
                "surname": user.profile.surname,
                "middle_name": user.profile.middle_name,
                "phone_number": user.profile.phone_number,
                "profile_picture": self._convert_to_public_url(user.profile.profile_picture) if user.profile.profile_picture else None,
                "language_preference": user.profile.language_preference or "en",
                "created_at": user.profile.created_at,
                "updated_at": user.profile.updated_at
            }
            from app.schemas.user_schema import UserProfile
            profile_obj = UserProfile(**profile_data)
        
        # Create UserSecurity object if security exists
        security_obj = None
        if user.security:
            security_data = {
                "user_id": str(user.user_id),
                "failed_login_attempts": user.security.failed_login_attempts or 0,
                "two_factor_enabled": user.security.two_factor_enabled or False,
                "last_login_at": user.security.last_login_at,
                "password_reset_token": None,  # Never expose this
                "password_reset_token_expires": None,  # Never expose this
                "last_login_ip": user.security.last_login_ip,
                "password_changed_at": user.security.password_changed_at,
                "created_at": user.security.created_at,
                "updated_at": user.security.updated_at
            }
            from app.schemas.user_schema import UserSecurity
            security_obj = UserSecurity(**security_data)
                    
        # Create UserResponse with proper nested objects
        response_data = {
            "user_id": str(user.user_id),  # Convert UUID to string
            "username": user.username,
            "email": user.email,
            "role_id": user.role_id,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "profile": profile_obj,
            "security": security_obj
        }
        
        return UserResponse(**response_data)

    def _convert_to_public_url(self, url: str) -> str:
        """Convert presigned URL to public URL if it's a MinIO/S3 URL"""
        if not url:
            return url
            
        # If it's already a direct public URL or external URL, leave it as is
        if (url.startswith("https://lh3.googleusercontent.com") or 
            url.startswith("https://googleusercontent.com") or
            not ("X-Amz-" in url or "presigned" in url)):
            return url
            
        # Extract object key from presigned URL
        try:
            # Parse the URL to get the object key
            if "bucket-production" in url and "accessible-environment" in url:
                # Extract the object key from Railway MinIO URL
                # Example: https://bucket-production-1bcc.up.railway.app/accessible-environment/profile_pictures/a5dc08f4.jpg?X-Amz-...
                parts = url.split("/")
                bucket_index = -1
                for i, part in enumerate(parts):
                    if "accessible-environment" in part:
                        bucket_index = i
                        break
                
                if bucket_index > 0 and bucket_index + 1 < len(parts):
                    # Get everything after the bucket name until the query parameters
                    object_path_parts = parts[bucket_index + 1:]
                    object_key = "/".join(object_path_parts).split("?")[0]
                    
                    # Generate public URL
                    from app.utils.external_storage import get_public_url
                    return get_public_url(object_key)
            
            return url  # Return original if we can't parse it
        except Exception as e:
            logger.warning(f"Failed to convert presigned URL to public URL: {e}")
            return url

    # Private helper methods
    def _generate_verification_token(self, user: User) -> str:
        """Generate email verification token."""
        return security_manager.create_access_token(
            {"sub": user.email, "type": "email_verification"},
            expires_delta=timedelta(hours=24)  # 24 hours expiry
        )

    def _get_verification_link(self, token: str) -> str:
        """Generate verification link."""
        return f"{settings.auth.frontend_base_url}/verify-email?token={token}"

    def generate_password_reset_token(self, user: User) -> str:
        """Generate password reset token for user."""
        with self.uow:
            # Generate token
            token = security_manager.create_access_token(
                {"sub": user.email, "type": "password_reset"},
                expires_delta=timedelta(hours=1)  # 1 hour expiry
            )
            
            # Store token in security table
            if not user.security:
                user.security = UserSecurity(user_id=user.user_id)
                self.uow.db.add(user.security)
                self.uow.db.flush()
            
            user.security.password_reset_token = token
            user.security.password_reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            self.uow.commit()
            
            return token

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using token."""
        with self.uow:
            # Find user by token
            user = self.uow.db.query(User).join(UserSecurity).filter(
                UserSecurity.password_reset_token == token,
                UserSecurity.password_reset_token_expires > datetime.now(timezone.utc)
            ).first()
            
            if not user:
                raise HTTPException(status_code=400, detail="Invalid or expired reset token")
            
            # Update password
            user.password_hash = security_manager.get_password_hash(new_password)
            
            # Clear reset token
            user.security.password_reset_token = None
            user.security.password_reset_token_expires = None
            user.security.password_changed_at = datetime.now(timezone.utc)
            
            self.uow.commit()
            return True

    def list_users_paginated(self, size: int, offset: int) -> Tuple[List[UserListResponse], int]:
        """List users paginated with proper format."""
        users_data, total = self.repo.get_minimal_users_paginated(size, offset)
        # Convert to UserListResponse objects
        user_responses = []
        for user_dict in users_data:
            if 'user_id' in user_dict:
                user_dict['user_id'] = str(user_dict['user_id'])
            # Add missing created_at if not present
            if 'created_at' not in user_dict:
                user_dict['created_at'] = datetime.now(timezone.utc)
            user_responses.append(UserListResponse(**user_dict))
        return user_responses, total

    def search_users(self, search_term: str, limit: int = 20, offset: int = 0) -> Tuple[List[UserListResponse], int]:
        """Search users with proper format."""
        fields = ["user_id", "username", "email", "first_name", "surname", "role_id", "is_active", "email_verified", "created_at"]
        users_data = self.repo.search_users(search_term, fields, limit, offset)
        total = self.repo.count_with_search(search_term)
        # Convert to UserListResponse objects
        user_responses = []
        for user_dict in users_data:
            if 'user_id' in user_dict:
                user_dict['user_id'] = str(user_dict['user_id'])
            # Add missing created_at if not present
            if 'created_at' not in user_dict:
                user_dict['created_at'] = datetime.now(timezone.utc)
            user_responses.append(UserListResponse(**user_dict))
        return user_responses, total

    def list_users_by_role(self, role_id: int, limit: int = 20, offset: int = 0) -> Tuple[List[UserListResponse], int]:
        """List users by role with proper format."""
        fields = ["user_id", "username", "email", "first_name", "surname", "role_id", "is_active", "email_verified", "created_at"]
        users_data = self.repo.get_users_by_role(role_id, fields, limit, offset)
        total = self.repo.count_by_role(role_id)
        # Convert to UserListResponse objects
        user_responses = []
        for user_dict in users_data:
            if 'user_id' in user_dict:
                user_dict['user_id'] = str(user_dict['user_id'])
            # Add missing created_at if not present
            if 'created_at' not in user_dict:
                user_dict['created_at'] = datetime.now(timezone.utc)
            user_responses.append(UserListResponse(**user_dict))
        return user_responses, total
