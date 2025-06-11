from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class LocationStats(BaseModel):
    """Statistics for locations in a specific category/region."""
    total_locations: int
    new_buildings: dict  # {"total": int, "good": int, "bad": int}
    old_buildings: dict  # {"total": int, "good": int, "bad": int}
    under_construction: int
    inactive: int
    closed: int

    model_config = ConfigDict(from_attributes=True)


class RegionStats(BaseModel):
    """Statistics for a specific region."""
    region_id: int
    region_name: str
    stats: LocationStats

    model_config = ConfigDict(from_attributes=True)


class CategoryStats(BaseModel):
    """Statistics for a specific category with regional breakdown."""
    category_id: int
    category_name: str
    regions: List[RegionStats]
    total_stats: LocationStats

    model_config = ConfigDict(from_attributes=True)


class BuildingAssessmentSummary(BaseModel):
    """Summary of building assessment scores for classification."""
    location_id: UUID
    location_name: str
    status: str  # 'new', 'old', 'under_construction', 'inactive', 'closed'
    region_id: int
    category_id: int
    average_score: Optional[float] = None
    total_assessments: int
    is_good: bool  # true if average_score >= 70

    model_config = ConfigDict(from_attributes=True) 