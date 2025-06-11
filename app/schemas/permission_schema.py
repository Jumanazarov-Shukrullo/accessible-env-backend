from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PermissionCreate(BaseModel):
    permission_name: str
    description: Optional[str] = None
    module: Optional[str] = None


class PermissionResponse(BaseModel):
    permission_id: int
    permission_name: str
    description: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    module: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
