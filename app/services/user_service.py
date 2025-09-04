"""User application service - orchestrates use cases using domain services."""

from datetime import timedelta
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.core.security import SecurityManager
from app.domain.exceptions import (
    InvalidCredentials,
    InvalidVerificationToken,
    UserAlreadyVerified,
    UserNotFound,
)
from app.domain.services.user_domain_service import UserDomainService
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User, UserProfile, UserSecurity
from app.schemas.user_schema import (
    InviteCreate,
    UserCreate,
    UserListResponse,
    UserProfileUpdate,
    UserResponse,
    UserUpdate,
)
from app.utils import cache
from app.utils.external_storage import MinioClient
from app.utils.logger import get_logger


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
                existing_email,
            )

            # Prepare user data
            user_data = user_in.dict()
            if not user_data.get("full_name"):
                user_data["full_name"] = (
                    self.domain_service.construct_full_name(
                        user_data["first_name"],
                        user_data["surname"],
                        user_data.get("middle_name"),
                    )
                )

            # Create user
            user = self.repo.create(user_data)
            token = self._generate_verification_token(user)
            verification_link = self._get_verification_link(token)

            self.uow.commit()

        cache.invalidate("users:")
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
                user = (
                    self.uow.db.query(User)
                    .options(joinedload(User.profile))
                    .filter(User.user_id == existing_user.user_id)
                    .first()
                )

                # Update or create profile
                if user.profile:
                    logger.info("Updating existing profile")
                    user.profile.first_name = google_info.get(
                        "given_name", user.profile.first_name
                    )
                    user.profile.surname = google_info.get(
                        "family_name", user.profile.surname
                    )

                    # Only update profile picture if user doesn't have a custom one
                    # (don't overwrite uploaded pictures with Google's default)
                    google_picture = google_info.get("picture", "")
                    current_picture = user.profile.profile_picture or ""

                    # Check if current picture is empty, default, or a Google avatar URL
                    # If user has uploaded a custom picture, preserve it
                    is_google_avatar = (
                        current_picture == ""
                        or current_picture.startswith(
                            "https://lh3.googleusercontent.com"
                        )
                        or current_picture.startswith(
                            "https://googleusercontent.com"
                        )
                        or current_picture.startswith(
                            "https://bucket-production"
                        )  # Railway MinIO bucket
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
                    full_name = (
                        f"{first_name} {surname}".strip()
                        if first_name or surname
                        else None
                    )

                    profile = UserProfile(
                        user_id=user.user_id,
                        first_name=first_name,
                        surname=surname,
                        full_name=full_name,
                        profile_picture=google_info.get("picture", ""),
                        language_preference="en",
                    )
                    self.uow.db.add(profile)

                self.uow.commit()
                logger.info(
                    f"Profile updated successfully for user: {user.username}"
                )
                return user
        else:
            logger.info("Creating new Google user")
            # Create new user with profile - use the existing
            # create_user_with_profile method
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
                language_preference="en",
            )

            with self.uow:
                # Create user using existing method but without the permission
                # checks
                temp_password = security_manager.generate_temp_password()
                password_hash = security_manager.get_password_hash(
                    temp_password
                )

                # Create core user record
                user = User(
                    username=user_data.username,
                    email=user_data.email,
                    password_hash=password_hash,
                    role_id=user_data.role_id,
                    is_active=True,
                    email_verified=True,  # Google users are pre-verified
                )
                self.uow.db.add(user)
                self.uow.db.flush()  # Get user_id

                # Create user profile
                full_name = (
                    f"{first_name} {surname}".strip()
                    if first_name or surname
                    else None
                )
                profile = UserProfile(
                    user_id=user.user_id,
                    first_name=first_name,
                    surname=surname,
                    full_name=full_name,
                    profile_picture=google_info.get("picture", ""),
                    language_preference="en",
                )
                self.uow.db.add(profile)

                # Create user security record
                security = UserSecurity(
                    user_id=user.user_id,
                    failed_login_attempts=0,
                    two_factor_enabled=False,
                )
                self.uow.db.add(security)

                self.uow.commit()

                logger.info(
                    f"New Google user created successfully: {user.username}"
                )
                return user

    def change_role(
        self, target_user_id: str, new_role: str, current_user: User
    ) -> UserResponse:
        """Change user role with validation."""
        logger.info(
            f"Changing role for user_id: {target_user_id} to role: {new_role}"
        )

        with self.uow:
            new_role_id = int(new_role)
            
            # Get user with relationships
            target_user = (
                self.uow.db.query(User)
                .options(
                    joinedload(User.profile),
                    joinedload(User.security),
                    joinedload(User.role),
                )
                .filter(User.user_id == target_user_id)
                .first()
            )
            
            if not target_user:
                raise UserNotFound(target_user_id)

            # Domain validation
            self.domain_service.validate_role_change(
                current_user, target_user, new_role_id
            )

            # Update role
            target_user.role_id = new_role_id
            self.uow.commit()
            
            # Return properly formatted response
            return self.get_user_response(target_user)

    def ban_user(self, target_user_id: str, current_user: User) -> UserResponse:
        """Ban user with validation."""
        logger.info(f"Banning user: {target_user_id}")

        with self.uow:
            # Get user with relationships
            target_user = (
                self.uow.db.query(User)
                .options(
                    joinedload(User.profile),
                    joinedload(User.security),
                    joinedload(User.role),
                )
                .filter(User.user_id == target_user_id)
                .first()
            )
            
            if not target_user:
                raise UserNotFound(target_user_id)

            # Domain validation
            self.domain_service.validate_user_ban(current_user, target_user)

            # Ban user
            target_user.is_active = False
            self.uow.commit()
            
            # Return properly formatted response
            return self.get_user_response(target_user)

    def unban_user(self, target_user_id: str) -> UserResponse:
        """Unban user."""
        logger.info(f"Unbanning user: {target_user_id}")

        with self.uow:
            # Get user with relationships
            target_user = (
                self.uow.db.query(User)
                .options(
                    joinedload(User.profile),
                    joinedload(User.security),
                    joinedload(User.role),
                )
                .filter(User.user_id == target_user_id)
                .first()
            )
            
            if not target_user:
                raise UserNotFound(target_user_id)

            target_user.is_active = True
            self.uow.commit()
            
            # Return properly formatted response
            return self.get_user_response(target_user)

    def update_profile(self, current_user: User, data: dict) -> UserResponse:
        """Update user profile data."""
        logger.info(f"Updating profile for user: {current_user.username}")

        with self.uow:
            # Reload user with relationships
            user = (
                self.uow.db.query(User)
                .options(
                    joinedload(User.profile),
                    joinedload(User.security),
                    joinedload(User.role),
                )
                .filter(User.user_id == current_user.user_id)
                .first()
            )

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Separate core user fields from profile fields
            user_fields = {"username", "email", "is_active", "email_verified"}
            profile_fields = {
                "first_name",
                "surname",
                "middle_name",
                "full_name",
                "phone_number",
                "profile_picture",
                "language_preference",
            }

            # Update core user fields
            user_updates = {
                k: v
                for k, v in data.items()
                if k in user_fields and v is not None
            }
            for field, value in user_updates.items():
                setattr(user, field, value)

            # Handle profile updates
            profile_updates = {
                k: v for k, v in data.items() if k in profile_fields
            }
            if profile_updates:
                # Get or create profile
                if not user.profile:
                    user.profile = UserProfile(
                        user_id=user.user_id, language_preference="en"
                    )
                    self.uow.db.add(user.profile)
                    self.uow.db.flush()

                # Update profile fields
                for field, value in profile_updates.items():
                    if hasattr(user.profile, field):
                        setattr(user.profile, field, value)

                # Auto-update full_name if first_name or surname changed
                if (
                    "first_name" in profile_updates
                    or "surname" in profile_updates
                ):
                    name_parts = []
                    if user.profile.first_name:
                        name_parts.append(user.profile.first_name)
                    if user.profile.middle_name:
                        name_parts.append(user.profile.middle_name)
                    if user.profile.surname:
                        name_parts.append(user.profile.surname)
                    user.profile.full_name = (
                        " ".join(name_parts) if name_parts else None
                    )

            self.uow.commit()

            # Return updated user response
            return self.get_user_response(user)

    def update_profile_picture(
        self, current_user: User, file: UploadFile
    ) -> str:
        """Update user profile picture."""
        logger.info(
            f"Updating profile picture for user: {current_user.username}"
        )

        with self.uow:
            # Reload user with profile relationship
            user = (
                self.uow.db.query(User)
                .options(joinedload(User.profile))
                .filter(User.user_id == current_user.user_id)
                .first()
            )

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Validate file
            if not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400, detail="File must be an image"
                )

            if file.size > 5 * 1024 * 1024:  # 5MB limit
                raise HTTPException(
                    status_code=400, detail="File size must be less than 5MB"
                )

            # Get or create profile
            if not user.profile:
                user.profile = UserProfile(
                    user_id=user.user_id, language_preference="en"
                )
                self.uow.db.add(user.profile)
                self.uow.db.flush()

            try:
                # Upload to MinIO and get public URL
                profile_picture_url = MinioClient.upload_profile_picture(
                    user.user_id, file
                )

                # Update profile with new picture URL
                user.profile.profile_picture = profile_picture_url
                self.uow.commit()

                logger.info(
                    f"Profile picture updated for user {
                        user.username}: {profile_picture_url}")
                return profile_picture_url

            except Exception as e:
                logger.error(
                    f"Failed to upload profile picture for user {
                        user.username}: {
                        str(e)}")
                raise HTTPException(
                    status_code=500, detail="Failed to upload profile picture"
                )

    def change_password(
        self, current_user: User, old_password: str, new_password: str
    ) -> None:
        """Change user password."""
        logger.info(f"Changing password for user: {current_user.username}")

        # Verify old password
        if not security_manager.verify_password(
            old_password, current_user.password_hash
        ):
            raise InvalidCredentials()

        # Validate new password
        self.domain_service.validate_password_strength(new_password)

        # Update password
        current_user.password_hash = security_manager.get_password_hash(
            new_password
        )
        self.repo.update(current_user)

    def create_user_with_profile(
        self, user_in: InviteCreate, created_by: User
    ) -> Tuple[User, str]:
        """Create user with profile and security tables"""
        with self.uow:
            # Check if email/username already exists
            existing_user = (
                self.uow.db.query(User)
                .filter(
                    or_(
                        User.email == user_in.email,
                        User.username == user_in.username,
                    )
                )
                .first()
            )

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email or username already exists",
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
                email_verified=False,
            )
            self.uow.db.add(user)
            self.uow.db.flush()  # Get user_id

            # Construct full_name from name components
            name_parts = []
            if user_in.first_name:
                name_parts.append(user_in.first_name.strip())
            if user_in.middle_name:
                name_parts.append(user_in.middle_name.strip())
            if user_in.surname:
                name_parts.append(user_in.surname.strip())
            full_name = " ".join(name_parts) if name_parts else None

            # Clean phone_number - convert empty string to None to avoid constraint violation
            clean_phone_number = user_in.phone_number.strip() if user_in.phone_number else None
            if clean_phone_number == "":
                clean_phone_number = None

            # Create user profile
            profile = UserProfile(
                user_id=user.user_id,
                first_name=user_in.first_name,
                surname=user_in.surname,
                middle_name=user_in.middle_name,
                full_name=full_name,
                phone_number=clean_phone_number,
                language_preference=user_in.language_preference,
            )
            self.uow.db.add(profile)

            # Create user security record
            security = UserSecurity(
                user_id=user.user_id,
                failed_login_attempts=0,
                two_factor_enabled=False,
            )
            self.uow.db.add(security)

            self.uow.commit()

            logger.info(
                f"User {
                    user.username} created successfully by {
                    created_by.username}")
            return user, temp_password

    def create_user_with_role(
        self, user_in: InviteCreate, created_by: User
    ) -> Tuple[User, str]:
        """Create user with specific role - alias for create_user_with_profile method."""
        return self.create_user_with_profile(user_in, created_by)

    def get_user_with_profile(self, user_id: str) -> Optional[UserResponse]:
        """Get user with profile and security data"""
        user = (
            self.uow.db.query(User)
            .options(
                joinedload(User.profile),
                joinedload(User.security),
                joinedload(User.role),
            )
            .filter(User.user_id == user_id)
            .first()
        )

        if not user:
            return None

        return self.get_user_response(user)

    def get_user_response(self, user: User) -> UserResponse:
        """Convert User model to UserResponse"""
        # Convert profile data if it exists
        profile_data = None
        if user.profile:
            profile_data = {
                "user_id": str(user.profile.user_id),
                "full_name": user.profile.full_name,
                "first_name": user.profile.first_name,
                "surname": user.profile.surname,
                "middle_name": user.profile.middle_name,
                "phone_number": user.profile.phone_number,
                "profile_picture": user.profile.profile_picture,
                "language_preference": user.profile.language_preference,
                "created_at": user.profile.created_at,
                "updated_at": user.profile.updated_at
            }

        # Convert security data if it exists
        security_data = None
        if user.security:
            security_data = {
                "user_id": str(user.security.user_id),
                "failed_login_attempts": user.security.failed_login_attempts,
                "two_factor_enabled": user.security.two_factor_enabled,
                "last_login_at": user.security.last_login_at,
                "password_reset_token": user.security.password_reset_token,
                "password_reset_token_expires": user.security.password_reset_token_expires,
                "last_login_ip": user.security.last_login_ip,
                "password_changed_at": user.security.password_changed_at,
                "created_at": user.security.created_at,
                "updated_at": user.security.updated_at
            }

        return UserResponse(
            user_id=str(user.user_id),
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            email_verified=user.email_verified,
            role_id=user.role_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
            profile=profile_data,
            security=security_data
        )

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email with all relationships"""
        return (
            self.uow.db.query(User)
            .options(
                joinedload(User.profile),
                joinedload(User.security),
                joinedload(User.role),
            )
            .filter(User.email == email)
            .first()
        )

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username with all relationships"""
        return (
            self.uow.db.query(User)
            .options(
                joinedload(User.profile),
                joinedload(User.security),
                joinedload(User.role),
            )
            .filter(User.username == username)
            .first()
        )

    def update_user_core(
        self, user_id: str, user_update: UserUpdate
    ) -> UserResponse:
        """Update core user data"""
        with self.uow:
            user = (
                self.uow.db.query(User).filter(User.user_id == user_id).first()
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            # Update core user fields
            for field, value in user_update.dict(exclude_unset=True).items():
                if hasattr(user, field) and value is not None:
                    setattr(user, field, value)

            self.uow.commit()
            return self.get_user_with_profile(user_id)

    def update_user_profile(
        self, user_id: str, profile_update: UserProfileUpdate
    ) -> UserResponse:
        """Update user profile data"""
        with self.uow:
            profile = (
                self.uow.db.query(UserProfile)
                .filter(UserProfile.user_id == user_id)
                .first()
            )
            if not profile:
                # Create profile if it doesn't exist
                profile = UserProfile(user_id=user_id)
                self.uow.db.add(profile)

            # Update profile fields
            for field, value in profile_update.dict(
                exclude_unset=True
            ).items():
                if hasattr(profile, field):
                    setattr(profile, field, value)

            # Update full_name if first_name or surname changed
            if (
                profile_update.first_name is not None
                or profile_update.surname is not None
            ):
                first_name = (
                    profile_update.first_name or profile.first_name or ""
                )
                surname = profile_update.surname or profile.surname or ""
                profile.full_name = f"{first_name} {surname}".strip() or None

            self.uow.commit()
            return self.get_user_with_profile(user_id)

    def authenticate_user(
        self, email: str, password: str, ip_address: str = None
    ) -> Optional[User]:
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
                    detail="Account locked due to too many failed login attempts",
                )

            # Verify password
            if not security_manager.verify_password(
                password, user.password_hash
            ):
                # Update failed login attempts
                if security:
                    security.failed_login_attempts += 1
                    self.uow.commit()
                return None

            # Successful login - reset failed attempts and update login info
            if security:
                security.failed_login_attempts = 0
                security.last_login_at = self.uow.db.execute(
                    "SELECT NOW()"
                ).scalar()
                security.last_login_ip = ip_address
                self.uow.commit()

            return user

    def get_users_paginated(
        self,
        page: int = 1,
        size: int = 50,
        search: str = None,
        role_id: int = None,
    ) -> Tuple[List[UserListResponse], int]:
        """Get paginated list of users with search and filtering"""
        query = self.uow.db.query(User).options(
            joinedload(User.profile),
            joinedload(User.security),
            joinedload(User.role),
        )

        # Apply filters
        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                UserProfile.first_name.ilike(f"%{search}%"),
                UserProfile.surname.ilike(f"%{search}%"),
                UserProfile.full_name.ilike(f"%{search}%"),
            )
            query = query.join(
                UserProfile, UserProfile.user_id == User.user_id, isouter=True
            ).filter(search_filter)

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
                "first_name": (
                    user.profile.first_name if user.profile else None
                ),
                "surname": user.profile.surname if user.profile else None,
                "last_login_at": (
                    user.security.last_login_at if user.security else None
                ),
            }
            user_responses.append(UserListResponse(**user_data))

        return user_responses, total

    def generate_password_reset_token(self, user: User) -> str:
        """Generate a password reset token for the user."""
        # Create token with user email and expiry
        token_data = {
            "email": user.email,
            "user_id": str(user.user_id),
            "type": "password_reset"
        }
        # Token expires in 1 hour
        expires_delta = timedelta(hours=1)
        return security_manager.create_access_token(token_data, expires_delta)

    def reset_password(self, token: str, new_password: str) -> None:
        """Reset user password using reset token."""
        try:
            # Verify token
            payload = security_manager.verify_token(token)
            if not payload or payload.get("type") != "password_reset":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired reset token"
                )
            
            user_email = payload.get("email")
            if not user_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid reset token"
                )
                
            # Get user and update password
            user = self.get_user_by_email(user_email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
                
            # Update password
            user.password_hash = security_manager.get_password_hash(new_password)
            self.repo.update(user)
            
        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset failed. Token may be invalid or expired."
            )
