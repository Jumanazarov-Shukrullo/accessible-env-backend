"""Domain exceptions that represent business rule violations."""

from typing import Optional


class DomainException(Exception):
    """Base exception for all domain-related errors."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


# User Domain Exceptions
class UserException(DomainException):
    """Base exception for user-related errors."""


class UserNotFound(UserException):
    """User not found in the system."""

    def __init__(self, identifier: str):
        super().__init__(f"User not found: {identifier}", "USER_NOT_FOUND")


class UserAlreadyExists(UserException):
    """User already exists in the system."""

    def __init__(self, field: str, value: str):
        super().__init__(
            f"User with {field} '{value}' already exists",
            "USER_ALREADY_EXISTS",
        )


class InvalidCredentials(UserException):
    """Invalid login credentials."""

    def __init__(self):
        super().__init__("Invalid credentials provided", "INVALID_CREDENTIALS")


class UserAlreadyVerified(UserException):
    """User email is already verified."""

    def __init__(self):
        super().__init__(
            "User email is already verified", "USER_ALREADY_VERIFIED"
        )


class InvalidVerificationToken(UserException):
    """Invalid email verification token."""

    def __init__(self):
        super().__init__(
            "Invalid or expired verification token",
            "INVALID_VERIFICATION_TOKEN",
        )


# Permission Domain Exceptions
class PermissionException(DomainException):
    """Base exception for permission-related errors."""


class InsufficientPermissions(PermissionException):
    """User lacks required permissions."""

    def __init__(self, action: str):
        super().__init__(
            f"Insufficient permissions for action: {action}",
            "INSUFFICIENT_PERMISSIONS",
        )


class CannotModifySuperAdmin(PermissionException):
    """Cannot modify superadmin users."""

    def __init__(self, action: str):
        super().__init__(
            f"Cannot {action} superadmin users", "CANNOT_MODIFY_SUPERADMIN"
        )


class CannotModifySelf(PermissionException):
    """Cannot modify own account in this way."""

    def __init__(self, action: str):
        super().__init__(
            f"Cannot {action} your own account", "CANNOT_MODIFY_SELF"
        )


class InvalidRoleAssignment(PermissionException):
    """Invalid role assignment attempt."""

    def __init__(self, reason: str):
        super().__init__(
            f"Invalid role assignment: {reason}", "INVALID_ROLE_ASSIGNMENT"
        )


# Location Domain Exceptions
class LocationException(DomainException):
    """Base exception for location-related errors."""


class LocationNotFound(LocationException):
    """Location not found in the system."""

    def __init__(self, location_id: str):
        super().__init__(
            f"Location not found: {location_id}", "LOCATION_NOT_FOUND"
        )


class InvalidLocationData(LocationException):
    """Invalid location data provided."""

    def __init__(self, field: str, reason: str):
        super().__init__(f"Invalid {field}: {reason}", "INVALID_LOCATION_DATA")


# Assessment Domain Exceptions
class AssessmentException(DomainException):
    """Base exception for assessment-related errors."""


class AssessmentNotFound(AssessmentException):
    """Assessment not found in the system."""

    def __init__(self, assessment_id: int):
        super().__init__(
            f"Assessment not found: {assessment_id}", "ASSESSMENT_NOT_FOUND"
        )


class InvalidAssessmentStatus(AssessmentException):
    """Invalid assessment status transition."""

    def __init__(self, current_status: str, attempted_action: str):
        super().__init__(
            f"Cannot {attempted_action} assessment with status: {current_status}",
            "INVALID_ASSESSMENT_STATUS",
        )


class AssessmentNotOwned(AssessmentException):
    """User doesn't own this assessment."""

    def __init__(self):
        super().__init__(
            "You don't have permission to modify this assessment",
            "ASSESSMENT_NOT_OWNED",
        )


# Geo Domain Exceptions
class GeoException(DomainException):
    """Base exception for geographical data errors."""


class RegionNotFound(GeoException):
    """Region not found in the system."""

    def __init__(self, region_id: int):
        super().__init__(f"Region not found: {region_id}", "REGION_NOT_FOUND")


class DistrictNotFound(GeoException):
    """District not found in the system."""

    def __init__(self, district_id: int):
        super().__init__(
            f"District not found: {district_id}", "DISTRICT_NOT_FOUND"
        )


class CityNotFound(GeoException):
    """City not found in the system."""

    def __init__(self, city_id: int):
        super().__init__(f"City not found: {city_id}", "CITY_NOT_FOUND")


class DuplicateGeoEntity(GeoException):
    """Duplicate geographical entity."""

    def __init__(self, entity_type: str, field: str, value: str):
        super().__init__(
            f"Duplicate {entity_type} {field}: {value}", "DUPLICATE_GEO_ENTITY"
        )


# Validation Domain Exceptions
class ValidationException(DomainException):
    """Base exception for validation errors."""


class InvalidDataFormat(ValidationException):
    """Invalid data format provided."""

    def __init__(self, field: str, expected_format: str):
        super().__init__(
            f"Invalid format for {field}, expected: {expected_format}",
            "INVALID_DATA_FORMAT",
        )


class RequiredFieldMissing(ValidationException):
    """Required field is missing."""

    def __init__(self, field: str):
        super().__init__(
            f"Required field missing: {field}", "REQUIRED_FIELD_MISSING"
        )


class InvalidRange(ValidationException):
    """Value is outside allowed range."""

    def __init__(
        self, field: str, min_val: float, max_val: float, actual: float
    ):
        super().__init__(
            f"{field} must be between {min_val} and {max_val}, got: {actual}",
            "INVALID_RANGE",
        )


# Resource Domain Exceptions
class ResourceException(DomainException):
    """Base exception for resource-related errors."""


class ResourceNotFound(ResourceException):
    """Generic resource not found."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} not found: {resource_id}", "RESOURCE_NOT_FOUND"
        )


class ResourceConflict(ResourceException):
    """Resource conflict during operation."""

    def __init__(self, resource_type: str, conflict_reason: str):
        super().__init__(
            f"{resource_type} conflict: {conflict_reason}", "RESOURCE_CONFLICT"
        )
