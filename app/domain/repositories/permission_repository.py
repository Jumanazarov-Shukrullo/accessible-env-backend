from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.permission_model import Permission
from app.schemas.permission_schema import PermissionCreate


class PermissionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, permission_id: int) -> Optional[Permission]:
        """Get permission by ID"""
        return (
            self.db.query(Permission)
            .filter(Permission.permission_id == permission_id)
            .first()
        )

    def get_by_name(self, permission_name: str) -> Optional[Permission]:
        return (
            self.db.query(Permission)
            .filter(Permission.permission_name == permission_name)
            .first()
        )

    def list(self) -> List[Permission]:
        """Get all permissions"""
        return self.db.query(Permission).all()

    def create(self, permission_in: PermissionCreate) -> Permission:
        new_permission: Permission = Permission(
            permission_name=permission_in.permission_name,
            description=permission_in.description,
            module=permission_in.module,
        )
        self.db.add(new_permission)
        self.db.commit()
        self.db.refresh(new_permission)
        return new_permission
