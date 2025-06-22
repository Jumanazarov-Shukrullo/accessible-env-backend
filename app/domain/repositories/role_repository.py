from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.permission_model import Permission
from app.models.role_model import Role
from app.models.role_permission_model import RolePermission


class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, role_data: dict) -> Role:
        role = Role(**role_data)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def list(self) -> List[Role]:
        return self.db.query(Role).all()

    def get(self, role_id: int) -> Optional[Role]:
        return self.db.query(Role).filter(Role.role_id == role_id).first()

    def update(self, role: Role, updates: dict) -> Role:
        for k, v in updates.items():
            setattr(role, k, v)
        self.db.commit()
        self.db.refresh(role)
        return role

    def delete(self, role: Role) -> None:
        self.db.delete(role)
        self.db.commit()

    def assign_permission(
        self, role: Role, permission: Permission
    ) -> RolePermission:
        rp = RolePermission(
            role_id=role.role_id, permission_id=permission.permission_id
        )
        self.db.add(rp)
        self.db.commit()
        self.db.refresh(rp)
        return rp

    def revoke_permission(self, role: Role, permission: Permission) -> None:
        self.db.query(RolePermission).filter_by(
            role_id=role.role_id, permission_id=permission.permission_id
        ).delete()
        self.db.commit()
