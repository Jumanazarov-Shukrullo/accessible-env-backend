"""Exception handlers to translate domain exceptions to HTTP responses."""

from fastapi import HTTPException, status
from app.domain.exceptions import (
    DomainException,
    UserException,
    UserNotFound,
    UserAlreadyExists,
    InvalidCredentials,
    UserAlreadyVerified,
    InvalidVerificationToken,
    PermissionException,
    InsufficientPermissions,
    CannotModifySuperAdmin,
    CannotModifySelf,
    InvalidRoleAssignment,
    LocationException,
    LocationNotFound,
    InvalidLocationData,
    AssessmentException,
    AssessmentNotFound,
    InvalidAssessmentStatus,
    AssessmentNotOwned,
    GeoException,
    RegionNotFound,
    DistrictNotFound,
    CityNotFound,
    DuplicateGeoEntity,
    ValidationException,
    InvalidDataFormat,
    RequiredFieldMissing,
    InvalidRange,
    ResourceException,
    ResourceNotFound,
    ResourceConflict
)


class DomainExceptionHandler:
    """Centralized handler for domain exceptions."""
    
    # Mapping of domain exceptions to HTTP status codes
    EXCEPTION_STATUS_MAP = {
        # User exceptions
        UserNotFound: status.HTTP_404_NOT_FOUND,
        UserAlreadyExists: status.HTTP_400_BAD_REQUEST,
        InvalidCredentials: status.HTTP_401_UNAUTHORIZED,
        UserAlreadyVerified: status.HTTP_400_BAD_REQUEST,
        InvalidVerificationToken: status.HTTP_400_BAD_REQUEST,
        
        # Permission exceptions
        InsufficientPermissions: status.HTTP_403_FORBIDDEN,
        CannotModifySuperAdmin: status.HTTP_403_FORBIDDEN,
        CannotModifySelf: status.HTTP_403_FORBIDDEN,
        InvalidRoleAssignment: status.HTTP_400_BAD_REQUEST,
        
        # Location exceptions
        LocationNotFound: status.HTTP_404_NOT_FOUND,
        InvalidLocationData: status.HTTP_400_BAD_REQUEST,
        
        # Assessment exceptions
        AssessmentNotFound: status.HTTP_404_NOT_FOUND,
        InvalidAssessmentStatus: status.HTTP_400_BAD_REQUEST,
        AssessmentNotOwned: status.HTTP_403_FORBIDDEN,
        
        # Geo exceptions
        RegionNotFound: status.HTTP_404_NOT_FOUND,
        DistrictNotFound: status.HTTP_404_NOT_FOUND,
        CityNotFound: status.HTTP_404_NOT_FOUND,
        DuplicateGeoEntity: status.HTTP_409_CONFLICT,
        
        # Validation exceptions
        InvalidDataFormat: status.HTTP_400_BAD_REQUEST,
        RequiredFieldMissing: status.HTTP_400_BAD_REQUEST,
        InvalidRange: status.HTTP_400_BAD_REQUEST,
        
        # Resource exceptions
        ResourceNotFound: status.HTTP_404_NOT_FOUND,
        ResourceConflict: status.HTTP_409_CONFLICT,
    }
    
    # Base exception type status codes
    BASE_EXCEPTION_STATUS_MAP = {
        UserException: status.HTTP_400_BAD_REQUEST,
        PermissionException: status.HTTP_403_FORBIDDEN,
        LocationException: status.HTTP_400_BAD_REQUEST,
        AssessmentException: status.HTTP_400_BAD_REQUEST,
        GeoException: status.HTTP_400_BAD_REQUEST,
        ValidationException: status.HTTP_400_BAD_REQUEST,
        ResourceException: status.HTTP_400_BAD_REQUEST,
    }
    
    @classmethod
    def handle_domain_exception(cls, exc: DomainException) -> HTTPException:
        """Convert domain exception to HTTP exception."""
        # Try to find specific exception mapping first
        status_code = cls.EXCEPTION_STATUS_MAP.get(type(exc))
        
        # Fall back to base exception type mapping
        if status_code is None:
            for base_type, base_status in cls.BASE_EXCEPTION_STATUS_MAP.items():
                if isinstance(exc, base_type):
                    status_code = base_status
                    break
        
        # Final fallback
        if status_code is None:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Create response with error details
        response_data = {
            "detail": exc.message,
            "error_code": exc.error_code,
            "type": exc.__class__.__name__
        }
        
        return HTTPException(
            status_code=status_code,
            detail=response_data
        )
    
    @classmethod
    def translate_exception(cls, exc: Exception) -> HTTPException:
        """Main entry point for exception translation."""
        if isinstance(exc, DomainException):
            return cls.handle_domain_exception(exc)
        
        # Handle other exception types if needed
        if isinstance(exc, ValueError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"detail": str(exc), "type": "ValueError"}
            )
        
        # Default to 500 for unexpected exceptions
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": "Internal server error", "type": "UnexpectedError"}
        )


def handle_service_exceptions(func):
    """Decorator to handle service exceptions in API endpoints."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DomainException as e:
            raise DomainExceptionHandler.handle_domain_exception(e)
        except Exception as e:
            raise DomainExceptionHandler.translate_exception(e)
    
    return wrapper


async def handle_async_service_exceptions(func):
    """Async decorator to handle service exceptions in API endpoints."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except DomainException as e:
            raise DomainExceptionHandler.handle_domain_exception(e)
        except Exception as e:
            raise DomainExceptionHandler.translate_exception(e)
    
    return wrapper 