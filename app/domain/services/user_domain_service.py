"""User domain service containing pure business logic."""

from typing import Optional

from app.core.constants import RoleID
from app.domain.exceptions import (
    CannotModifySelf,
    CannotModifySuperAdmin,
    InsufficientPermissions,
    InvalidCredentials,
    InvalidRoleAssignment,
    UserAlreadyExists,
)
from app.models.user_model import User


class UserDomainService:
    """Pure domain service for user business logic."""

    @staticmethod
    def validate_user_registration(
        username: str,
        email: str,
        existing_username: Optional[User],
        existing_email: Optional[User],
    ) -> None:
        """Validate user registration data."""
        if existing_username:
            raise UserAlreadyExists("username", username)

        if existing_email:
            raise UserAlreadyExists("email", email)

    @staticmethod
    def construct_full_name(
        first_name: str, surname: str, middle_name: Optional[str] = None
    ) -> str:
        """Construct a full name from components."""
        if middle_name:
            return f"{first_name} {middle_name} {surname}"
        return f"{first_name} {surname}"

    @staticmethod
    def validate_role_change(
        actor: User, target: User, new_role_id: int
    ) -> None:
        """Validate if a role change is allowed."""
        # Cannot modify superadmin users
        if target.role_id == RoleID.SUPERADMIN.value:
            raise CannotModifySuperAdmin("change role of")

        # Cannot modify yourself
        if target.user_id == actor.user_id:
            raise CannotModifySelf("change role of")

        # Only superadmins can promote to superadmin
        if (
            new_role_id == RoleID.SUPERADMIN.value
            and actor.role_id != RoleID.SUPERADMIN.value
        ):
            raise InvalidRoleAssignment(
                "Only superadmins can promote to superadmin"
            )

    @staticmethod
    def validate_user_ban(actor: User, target: User) -> None:
        """Validate if a user ban is allowed."""
        # Cannot ban superadmin users
        if target.role_id == RoleID.SUPERADMIN.value:
            raise CannotModifySuperAdmin("ban")

        # Cannot ban yourself
        if target.user_id == actor.user_id:
            raise CannotModifySelf("ban")

    @staticmethod
    def validate_invite_permission(inviter: User, target_role_id: int) -> None:
        """Validate if user can invite someone with the specified role."""
        # Only allow inviting admins or superadmins
        if target_role_id not in (RoleID.ADMIN.value, RoleID.SUPERADMIN.value):
            raise InvalidRoleAssignment(
                "Can only invite admins or superadmins"
            )

        # Only superadmins can invite other superadmins
        if (
            target_role_id == RoleID.SUPERADMIN.value
            and inviter.role_id != RoleID.SUPERADMIN.value
        ):
            raise InsufficientPermissions("invite superadmins")

    @staticmethod
    def validate_inspector_assignment(assigner: User, inspector: User) -> None:
        """Validate if inspector assignment is allowed."""
        # Only superadmin can assign inspectors
        if assigner.role_id != RoleID.SUPERADMIN.value:
            raise InsufficientPermissions("assign inspectors")

        # Only admin and superadmin users can be assigned as inspectors
        if inspector.role_id not in [
            RoleID.SUPERADMIN.value,
            RoleID.ADMIN.value,
        ]:
            raise InvalidRoleAssignment(
                "Only admin and superadmin users can be assigned as inspectors"
            )

        # Admins can't assign themselves as inspectors
        if assigner.user_id == inspector.user_id:
            raise CannotModifySelf("assign as inspector")

    @staticmethod
    def validate_password_strength(password: str) -> None:
        """Validate password meets security requirements."""
        if len(password) < 8:
            raise InvalidCredentials()  # Could create more specific exception

        # Add more password validation rules as needed
        # has_upper = any(c.isupper() for c in password)
        # has_lower = any(c.islower() for c in password)
        # has_digit = any(c.isdigit() for c in password)
        # if not (has_upper and has_lower and has_digit):
        #     raise InvalidCredentials()

    @staticmethod
    def validate_user_update_fields(fields: dict, allowed_fields: set) -> dict:
        """Validate and filter user update fields."""
        filtered_fields = {}

        for key, value in fields.items():
            if key not in allowed_fields:
                continue

            # Treat empty strings as None to satisfy DB constraints
            if isinstance(value, str) and not value.strip():
                value = None

            if value is not None:
                filtered_fields[key] = value

        return filtered_fields

    @staticmethod
    def should_update_full_name(updated_fields: dict) -> bool:
        """Check if full name should be recalculated."""
        name_fields = {"first_name", "surname", "middle_name"}
        return any(field in updated_fields for field in name_fields)

    @staticmethod
    def validate_admin_comment_permission(user: User) -> None:
        """Validate if user can modify admin comments."""
        if user.role_id not in (RoleID.ADMIN.value, RoleID.SUPERADMIN.value):
            raise InsufficientPermissions("modify admin comments")
