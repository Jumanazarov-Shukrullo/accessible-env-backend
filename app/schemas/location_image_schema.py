from pydantic import BaseModel, ConfigDict


class LocationImageCreate(BaseModel):
    image_url: str
    description: str | None = None
    position: int = 0


class LocationImageOut(LocationImageCreate):
    image_id: int
    model_config = ConfigDict(from_attributes=True)


class LocationImageResponse(BaseModel):
    # ... fields ...
    model_config = ConfigDict(from_attributes=True)
