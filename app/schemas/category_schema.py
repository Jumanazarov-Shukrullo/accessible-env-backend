from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CategorySchema:
    class Create(BaseModel):
        category_name: str
        slug: Optional[str] = None
        parent_category_id: Optional[int] = None
        description: Optional[str] = None
        icon: Optional[str] = "Building2"  # Default to Building2 icon

    class Update(BaseModel):
        category_name: Optional[str] = None
        slug: Optional[str] = None
        parent_category_id: Optional[int] = None
        description: Optional[str] = None
        icon: Optional[str] = None

    class Out(BaseModel):
        category_id: int
        category_name: str
        slug: Optional[str] = None
        parent_category_id: Optional[int] = None
        description: Optional[str] = None
        icon: Optional[str] = None
        children: List["CategorySchema.Out"] = []

        model_config = ConfigDict(from_attributes=True)
