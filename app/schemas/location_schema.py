from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field, validator


class InspectorOut(BaseModel):
    user_id: UUID
    username: Optional[str] = None
    first_name: Optional[str] = None
    surname: Optional[str] = None
    middle_name: Optional[str] = None
    email: Optional[str] = None
    assigned_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def full_name(self) -> Optional[str]:
        if self.first_name and self.surname:
            middle = f" {self.middle_name} " if self.middle_name else " "
            return f"{self.first_name}{middle}{self.surname}".replace(
                "  ", " "
            ).strip()
        return None


class LocationBase(BaseModel):
    location_name: str
    address: str
    latitude: Decimal
    longitude: Decimal
    category_id: int
    region_id: int
    district_id: int
    city_id: Optional[int] = None
    status: str = "active"

    @validator("status")
    def validate_status(cls, v):
        allowed_statuses = [
            "active",
            "inactive",
            "new",
            "old",
            "under_construction",
            "closed",
        ]
        if v not in allowed_statuses:
            raise ValueError(
                f'Status must be one of: {", ".join(allowed_statuses)}'
            )
        return v

    @validator("latitude")
    def validate_latitude(cls, v):
        if v < -90 or v > 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @validator("longitude")
    def validate_longitude(cls, v):
        if v < -180 or v > 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v


class LocationCreate(LocationBase):
    """Data needed to create a new location."""

    contact_info: Optional[str] = None
    website_url: Optional[str] = None
    operating_hours: Optional[Dict] = None
    description: Optional[str] = None


class LocationUpdate(BaseModel):
    """Data that can be updated for a location."""

    location_name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    category_id: Optional[int] = None
    region_id: Optional[int] = None
    district_id: Optional[int] = None
    city_id: Optional[int] = None
    status: Optional[str] = None

    # Details fields that can be updated
    contact_info: Optional[str] = None
    website_url: Optional[str] = None
    operating_hours: Optional[Dict] = None
    description: Optional[str] = None


class LocationCore(LocationBase):
    location_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LocationDetailsBase(BaseModel):
    contact_info: Optional[str] = None
    website_url: Optional[str] = None
    operating_hours: Optional[Dict] = None
    description: Optional[str] = None


class LocationDetailsCreate(LocationDetailsBase):
    pass


class LocationDetailsUpdate(LocationDetailsBase):
    pass


class LocationDetails(LocationDetailsBase):
    location_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LocationStatsBase(BaseModel):
    accessibility_score: Optional[Decimal] = None
    total_reviews: int = 0
    total_ratings: int = 0
    average_rating: Optional[Decimal] = None
    last_assessment_date: Optional[datetime] = None


class LocationStats(LocationStatsBase):
    location_id: str
    updated_at: datetime

    class Config:
        from_attributes = True


class LocationImageBase(BaseModel):
    image_url: str
    description: Optional[str] = None


class LocationImageCreate(LocationImageBase):
    pass


class LocationImage(LocationImageBase):
    image_id: int
    location_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class LocationRatingBase(BaseModel):
    rating_value: int

    @validator("rating_value")
    def validate_rating(cls, v):
        if v < 0 or v > 10:
            raise ValueError("Rating must be between 0 and 10")
        return v


class LocationRatingCreate(LocationRatingBase):
    location_id: str


class LocationRating(LocationRatingBase):
    rating_id: int
    location_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FavouriteBase(BaseModel):
    location_id: str


class FavouriteCreate(FavouriteBase):
    pass


class Favourite(FavouriteBase):
    favorite_id: int
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class LocationResponse(LocationCore):
    """Complete location response with details and stats"""

    details: Optional[LocationDetails] = None
    stats: Optional[LocationStats] = None
    images: List[LocationImage] = []
    inspectors: List[InspectorOut] = []

    # Flattened fields from details for easy frontend access
    contact_info: Optional[str] = None
    website_url: Optional[str] = None
    operating_hours: Optional[Dict] = None
    description: Optional[str] = None

    # Flattened fields from stats for easy frontend access
    accessibility_score: Optional[Decimal] = None
    total_reviews: int = 0
    total_ratings: int = 0
    average_rating: Optional[Decimal] = None
    last_assessment_date: Optional[datetime] = None

    # Category and region names for proper display
    category_name: Optional[str] = None
    region_name: Optional[str] = None
    district_name: Optional[str] = None
    city_name: Optional[str] = None

    # Breadcrumb navigation data
    breadcrumb: Optional[list[dict]] = None

    # Primary image URL for header display
    primary_image_url: Optional[str] = None

    class Config:
        from_attributes = True

    def __init__(self, **data):
        # Flatten details fields to top level for backward compatibility
        if "details" in data and data["details"]:
            details = data["details"]
            if hasattr(details, "contact_info"):  # SQLAlchemy object
                data["contact_info"] = details.contact_info
                data["website_url"] = details.website_url
                data["operating_hours"] = details.operating_hours
                data["description"] = details.description
            elif isinstance(details, dict):  # Dictionary
                data["contact_info"] = details.get("contact_info")
                data["website_url"] = details.get("website_url")
                data["operating_hours"] = details.get("operating_hours")
                data["description"] = details.get("description")

        # Flatten stats fields to top level for backward compatibility
        if "stats" in data and data["stats"]:
            stats = data["stats"]
            if hasattr(stats, "accessibility_score"):  # SQLAlchemy object
                data["accessibility_score"] = stats.accessibility_score
                data["total_reviews"] = stats.total_reviews
                data["total_ratings"] = stats.total_ratings
                data["average_rating"] = stats.average_rating
                data["last_assessment_date"] = stats.last_assessment_date
            elif isinstance(stats, dict):  # Dictionary
                data["accessibility_score"] = stats.get("accessibility_score")
                data["total_reviews"] = stats.get("total_reviews", 0)
                data["total_ratings"] = stats.get("total_ratings", 0)
                data["average_rating"] = stats.get("average_rating")
                data["last_assessment_date"] = stats.get(
                    "last_assessment_date"
                )

        super().__init__(**data)


class LocationDetailResponse(LocationResponse):
    """Detailed location response with additional info"""

    category_name: Optional[str] = None
    region_name: Optional[str] = None
    district_name: Optional[str] = None
    city_name: Optional[str] = None
    breadcrumb: Optional[list[dict]] = None

    class Config:
        from_attributes = True


class LocationListResponse(BaseModel):
    """Response model for location list endpoints"""
    location_id: UUID
    location_name: str
    address: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    status: str
    accessibility_score: Optional[float] = None
    average_rating: Optional[float] = None
    total_reviews: int = 0
    category_name: Optional[str] = None
    region_name: Optional[str] = None
    district_name: Optional[str] = None
    city_name: Optional[str] = None
    primary_image_url: Optional[str] = None
    
    # Enhanced fields for editing and admin display
    category_id: Optional[int] = None
    region_id: Optional[int] = None
    district_id: Optional[int] = None
    city_id: Optional[int] = None
    contact_info: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    operating_hours: Optional[Dict] = None
    
    # Inspector information
    inspector_count: int = 0
    inspectors: List[InspectorOut] = []

    model_config = ConfigDict(from_attributes=True)


class LocationSearchResponse(BaseModel):
    """Location search response with distance"""

    location_id: str
    location_name: str
    address: str
    latitude: Decimal
    longitude: Decimal
    distance_km: Optional[Decimal] = None
    accessibility_score: Optional[Decimal] = None
    average_rating: Optional[Decimal] = None
    category_name: Optional[str] = None
    primary_image_url: Optional[str] = None

    class Config:
        from_attributes = True


class LocationBulkUpdate(BaseModel):
    location_ids: List[str]
    status: str

    @validator("status")
    def validate_status(cls, v):
        allowed_statuses = [
            "active",
            "inactive",
            "new",
            "old",
            "under_construction",
            "closed",
        ]
        if v not in allowed_statuses:
            raise ValueError(
                f'Status must be one of: {", ".join(allowed_statuses)}'
            )
        return v


class LocationAssignInspector(BaseModel):
    location_id: str
    inspector_id: str


class LocationFilter(BaseModel):
    """Query parameters for location filtering."""

    category_id: Optional[int] = None
    region_id: Optional[int] = None
    district_id: Optional[int] = None
    city_id: Optional[int] = None
    status: Optional[str] = None
    min_accessibility_score: Optional[float] = None
    max_accessibility_score: Optional[float] = None
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None
    has_assessments: Optional[bool] = None


class LocationSearch(BaseModel):
    query: Optional[str] = None
    center_lat: Optional[Decimal] = None
    center_lng: Optional[Decimal] = None
    radius_km: Optional[int] = 10
    filters: Optional[LocationFilter] = None
    limit: int = 50
    offset: int = 0


class PaginatedLocations(BaseModel):
    items: List[LocationListResponse]
    total: int
    page: int
    size: int
    pages: int

    class Config:
        from_attributes = True
