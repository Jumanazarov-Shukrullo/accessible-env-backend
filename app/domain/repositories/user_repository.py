from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.security import SecurityManager
from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.domain.repositories.iuser_repository import IUserRepository
from app.models.user_model import User
from app.utils.cache import cache
from app.utils.logger import get_logger


logger = get_logger("user_repository")


class UserRepository(SQLAlchemyRepository[User, str], IUserRepository):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.user_id == user_id).first()

    def get_all(self) -> List[User]:
        return self.db.query(User).all()

    def create(self, user_data: dict) -> User:
        """
        Create a new user with profile and security data in normalized tables.
        """
        # Separate core user data from profile and security data
        core_fields = {
            "username",
            "email",
            "role_id",
            "is_active",
            "email_verified",
        }
        profile_fields = {
            "first_name",
            "surname",
            "middle_name",
            "full_name",
            "phone_number",
            "profile_picture",
            "language_preference",
        }
        security_fields = {
            "last_login_at",
            "failed_login_attempts",
            "password_reset_token",
            "password_reset_token_expires",
            "two_factor_enabled",
            "last_login_ip",
            "password_changed_at",
        }

        # Extract password and hash it
        plain_password = user_data.pop("password", None) or user_data.pop(
            "password_hash", None
        )
        if plain_password is None:
            raise ValueError("Password is required")

        # Prepare core user data
        core_data = {k: v for k, v in user_data.items() if k in core_fields}
        core_data["password_hash"] = SecurityManager.get_password_hash(
            plain_password
        )

        # Handle role_id = 0 case
        if "role_id" in core_data and core_data["role_id"] == 0:
            core_data["role_id"] = None

        # Create user
        new_user = User(**core_data)
        self.db.add(new_user)
        self.db.flush()  # Flush to get user_id

        # Create profile if profile data exists
        profile_data = {
            k: v
            for k, v in user_data.items()
            if k in profile_fields and v is not None
        }
        if profile_data or any(k in user_data for k in profile_fields):
            from app.models.user_model import UserProfile

            profile_data["user_id"] = new_user.user_id
            if "language_preference" not in profile_data:
                profile_data["language_preference"] = "en"
            profile = UserProfile(**profile_data)
            self.db.add(profile)

        # Create security record if security data exists
        security_data = {
            k: v
            for k, v in user_data.items()
            if k in security_fields and v is not None
        }
        if security_data or any(k in user_data for k in security_fields):
            from app.models.user_model import UserSecurity

            security_data["user_id"] = new_user.user_id
            security = UserSecurity(**security_data)
            self.db.add(security)

        self.db.commit()
        self.db.refresh(new_user)

        # Invalidate cache
        cache.invalidate("users")
        cache.invalidate("minimal_users")

        return new_user

    def update(self, user: User) -> User:
        self.db.commit()
        self.db.refresh(user)

        # Invalidate specific user and user lists
        cache.invalidate(f"user:{user.user_id}")
        cache.invalidate("users")
        cache.invalidate("minimal_users")

        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()

        # Invalidate cache entries
        cache.invalidate(f"user:{user.user_id}")
        cache.invalidate("users")
        cache.invalidate("minimal_users")

    def get_by_password_reset_token(self, token: str) -> Optional[User]:
        from app.models.user_model import UserSecurity

        return (
            self.db.query(User)
            .join(UserSecurity, User.user_id == UserSecurity.user_id)
            .filter(UserSecurity.password_reset_token == token)
            .filter(
                UserSecurity.password_reset_token_expires
                > datetime.now(timezone.utc)
            )
            .first()
        )

    def get_paginated(self, limit: int, offset: int) -> List[User]:
        return (
            self.db.query(User)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @cache.cacheable(lambda self,
                     fields,
                     limit=20,
                     offset=0: f"users:fields:{','.join(fields)}:{limit}:{offset}",
                     ttl=300,
                     )
    def get_specific_fields(
        self, fields: List[str], limit: int = 20, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Fetch only specific fields of user records, joining profile and security tables as needed"""
        logger.info(
            f"Fetching user fields {fields} with limit {limit}, offset {offset}")
        start_time = datetime.now()

        from app.models.user_model import UserProfile, UserSecurity

        # Separate fields by table
        user_fields = [f for f in fields if hasattr(User, f)]
        profile_fields = [
            f for f in fields if hasattr(UserProfile, f) and f != "user_id"
        ]
        security_fields = [
            f for f in fields if hasattr(UserSecurity, f) and f != "user_id"
        ]

        # Build query with necessary joins
        query = self.db.query(User)
        if profile_fields:
            query = query.outerjoin(
                UserProfile, User.user_id == UserProfile.user_id
            )
        if security_fields:
            query = query.outerjoin(
                UserSecurity, User.user_id == UserSecurity.user_id
            )

        users = (
            query.order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        # Convert to dictionary format
        users_data = []
        for user in users:
            user_dict = {}
            # Add user fields
            for field in user_fields:
                user_dict[field] = getattr(user, field, None)
            # Add profile fields
            for field in profile_fields:
                if user.profile:
                    user_dict[field] = getattr(user.profile, field, None)
                else:
                    user_dict[field] = None
            # Add security fields
            for field in security_fields:
                if user.security:
                    user_dict[field] = getattr(user.security, field, None)
                else:
                    user_dict[field] = None
            users_data.append(user_dict)

        end_time = datetime.now()
        logger.info(
            f"User query completed in {
                (
                    end_time -
                    start_time).total_seconds():.2f} seconds, found {
                len(users_data)} users")
        return users_data

    @cache.cacheable(
        lambda self,
        role_id,
        fields,
        limit=20,
        offset=0: f"users:role:{role_id}:fields:{
            ','.join(fields)}:{limit}:{offset}",
        ttl=300,
    )
    def get_users_by_role(
        self, role_id: int, fields: List[str], limit: int = 20, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get users with specific role, returning only needed fields from joined tables"""
        logger.info(f"Fetching users with role {role_id}")
        start_time = datetime.now()

        from app.models.user_model import UserProfile, UserSecurity

        # Separate fields by table
        user_fields = [f for f in fields if hasattr(User, f)]
        profile_fields = [
            f for f in fields if hasattr(UserProfile, f) and f != "user_id"
        ]
        security_fields = [
            f for f in fields if hasattr(UserSecurity, f) and f != "user_id"
        ]

        # Build query with necessary joins
        query = self.db.query(User).filter(User.role_id == role_id)
        if profile_fields:
            query = query.outerjoin(
                UserProfile, User.user_id == UserProfile.user_id
            )
        if security_fields:
            query = query.outerjoin(
                UserSecurity, User.user_id == UserSecurity.user_id
            )

        users = (
            query.order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        # Convert to dictionary format
        users_data = []
        for user in users:
            user_dict = {}
            # Add user fields
            for field in user_fields:
                user_dict[field] = getattr(user, field, None)
            # Add profile fields
            for field in profile_fields:
                if user.profile:
                    user_dict[field] = getattr(user.profile, field, None)
                else:
                    user_dict[field] = None
            # Add security fields
            for field in security_fields:
                if user.security:
                    user_dict[field] = getattr(user.security, field, None)
                else:
                    user_dict[field] = None
            users_data.append(user_dict)

        end_time = datetime.now()
        logger.info(
            f"Role-based user query completed in {
                (
                    end_time -
                    start_time).total_seconds():.2f} seconds, found {
                len(users_data)} users")
        return users_data

    @cache.cacheable(
        lambda self,
        search_term,
        fields,
        limit=20,
        offset=0: f"users:search:{search_term}:fields:{
            ','.join(fields)}:{limit}:{offset}",
        ttl=300,
    )
    def search_users(
        self,
        search_term: str,
        fields: List[str],
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Search users by username, email, and profile fields"""
        logger.info(f"Searching users with term '{search_term}'")
        start_time = datetime.now()

        from app.models.user_model import UserProfile

        # Separate user fields from profile fields
        user_fields = [f for f in fields if hasattr(User, f)]
        profile_fields = [
            f for f in fields if hasattr(UserProfile, f) and f != "user_id"
        ]

        search_pattern = f"%{search_term}%"

        # Build the query with left join to profile
        query = self.db.query(User).outerjoin(
            UserProfile, User.user_id == UserProfile.user_id
        )

        # Add search filters
        search_filters = [
            User.username.ilike(search_pattern),
            User.email.ilike(search_pattern),
        ]

        # Add profile search filters if they exist
        if hasattr(UserProfile, "first_name"):
            search_filters.append(UserProfile.first_name.ilike(search_pattern))
        if hasattr(UserProfile, "surname"):
            search_filters.append(UserProfile.surname.ilike(search_pattern))
        if hasattr(UserProfile, "full_name"):
            search_filters.append(UserProfile.full_name.ilike(search_pattern))

        users = (
            query.filter(or_(*search_filters))
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        # Convert to dictionary format
        users_data = []
        for user in users:
            user_dict = {}
            # Add user fields
            for field in user_fields:
                user_dict[field] = getattr(user, field, None)
            # Add profile fields
            if user.profile:
                for field in profile_fields:
                    user_dict[field] = getattr(user.profile, field, None)
            else:
                # Fill with None if no profile
                for field in profile_fields:
                    user_dict[field] = None
            users_data.append(user_dict)

        end_time = datetime.now()
        logger.info(
            f"Search users query completed in {
                (
                    end_time -
                    start_time).total_seconds():.2f} seconds, found {
                len(users_data)} users")
        return users_data

    @cache.cacheable(
        lambda self, role_id=None: f"users:count:role:{role_id}", ttl=300
    )
    def count_by_role(self, role_id: int = None) -> int:
        """Count users with specific role or all users if role_id is None"""
        logger.info(f"Counting users with role {role_id}")
        query = self.db.query(func.count(User.user_id))
        if role_id is not None:
            query = query.filter(User.role_id == role_id)
        return query.scalar()

    @cache.cacheable(
        lambda self, search_term: f"users:count:search:{search_term}", ttl=300
    )
    def count_with_search(self, search_term: str) -> int:
        """Count users matching search criteria"""
        logger.info(f"Counting users matching search '{search_term}'")
        from app.models.user_model import UserProfile

        search_pattern = f"%{search_term}%"

        # Build query with join to profile
        query = self.db.query(func.count(User.user_id.distinct())).outerjoin(
            UserProfile, User.user_id == UserProfile.user_id
        )

        # Add search filters
        search_filters = [
            User.username.ilike(search_pattern),
            User.email.ilike(search_pattern),
        ]

        # Add profile search filters
        search_filters.extend(
            [
                UserProfile.first_name.ilike(search_pattern),
                UserProfile.surname.ilike(search_pattern),
                UserProfile.full_name.ilike(search_pattern),
            ]
        )

        return query.filter(or_(*search_filters)).scalar()

    @cache.cacheable(
        lambda self, limit=20, offset=0: f"users:minimal:{limit}:{offset}",
        ttl=300,
    )
    def get_minimal_users_paginated(
        self, limit: int, offset: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get paginated users with all required fields for UserResponse model"""
        logger.info(
            f"Fetching minimal users paginated with limit {limit}, offset {offset}")
        start_time = datetime.now()

        required_fields = [
            "user_id",
            "username",
            "email",
            "first_name",
            "surname",
            "middle_name",
            "role_id",
            "is_active",
            "email_verified",
            "created_at",
            "profile_picture",
            "phone_number",
            "language_preference",
        ]
        users = self.get_specific_fields(required_fields, limit, offset)
        total = self.count()

        end_time = datetime.now()
        logger.info(
            f"Minimal users query completed in {(end_time - start_time).total_seconds():.2f} seconds"
        )
        return users, total

    @cache.cacheable(lambda self: "users:count", ttl=300)
    def count(self) -> int:
        logger.info("Counting all users")
        return self.db.query(User).count()
