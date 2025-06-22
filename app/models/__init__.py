# Import order is important to avoid circular dependencies
# Core models first
from app.models.role_model import Role
from app.models.user_model import User, UserProfile, UserSecurity

# Geographic models
from app.models.region_model import Region
from app.models.district_model import District
from app.models.city_model import City

# Category model
from app.models.category_model import Category

# Location models
from app.models.location_model import Location, LocationDetails, LocationStats
from app.models.location_images_model import LocationImage

# Location Inspector model
from app.models.location_inspector_model import LocationInspector

# Favourite model
from app.models.favourite_model import Favourite

# Rating model (imported after user and location models)
from app.models.rating_model import LocationRating

# Other models
from app.models.review_model import Review
from app.models.notification_model import Notification
from app.models.comment_model import Comment

# Statistics model
from app.models.statistics_model import Statistic

# Assessment models
from app.models.assessment_model import (
    AccessibilityCriteria,
    AssessmentSet,
    SetCriteria,
    LocationSetAssessment,
    LocationAssessment,
    AssessmentComment,
    AssessmentImage,
)

__all__ = [
    "Role",
    "User",
    "UserProfile",
    "UserSecurity",
    "Region",
    "District",
    "City",
    "Category",
    "Location",
    "LocationDetails",
    "LocationStats",
    "LocationImage",
    "LocationInspector",
    "Favourite",
    "LocationRating",
    "Review",
    "Notification",
    "Comment",
    "Statistic",
    "AccessibilityCriteria",
    "AssessmentSet",
    "SetCriteria",
    "LocationSetAssessment",
    "LocationAssessment",
    "AssessmentComment",
    "AssessmentImage",
]
