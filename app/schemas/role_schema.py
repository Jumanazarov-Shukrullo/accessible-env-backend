from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class PermissionBase(BaseModel):
    permission_id: int
    permission_name: str
    description: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None


class RoleCreate(BaseModel):
    role_name: str
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    role_name: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    role_id: int
    role_name: str
    description: Optional[str] = None
    level: int
    is_system_role: bool
    user_count: Optional[int] = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    permissions: List[PermissionBase] = []

    model_config = ConfigDict(from_attributes=True)
