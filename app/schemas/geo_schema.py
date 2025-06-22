from typing import Optional

from pydantic import BaseModel, ConfigDict


class RegionSchema:
    class Create(BaseModel):
        region_name: str
        region_code: str
        description: Optional[str] = None
        area: Optional[float] = None
        population: Optional[int] = None
        model_config = ConfigDict(from_attributes=True)

    class Out(Create):
        region_id: int


class DistrictSchema:
    class Create(BaseModel):
        district_name: str
        district_code: str
        region_id: int
        description: Optional[str] = None
        area: Optional[float] = None
        population: Optional[int] = None
        model_config = ConfigDict(from_attributes=True)

    class Out(Create):
        district_id: int


class CitySchema:
    class Create(BaseModel):
        city_name: str
        region_id: int
        district_id: int
        city_code: Optional[str] = None
        population: Optional[int] = None
        model_config = ConfigDict(from_attributes=True)

    class Out(Create):
        city_id: int


class PaginatedRegions(BaseModel):
    items: list[RegionSchema.Out]
    total: int
    model_config = ConfigDict(from_attributes=True)


class PaginatedDistricts(BaseModel):
    items: list[DistrictSchema.Out]
    total: int
    model_config = ConfigDict(from_attributes=True)


class PaginatedCities(BaseModel):
    items: list[CitySchema.Out]
    total: int
    model_config = ConfigDict(from_attributes=True)
