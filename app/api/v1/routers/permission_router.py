from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.dependencies import require_roles
from app.core.constants import RoleID
from app.db.session import get_db
from app.domain.repositories.permission_repository import PermissionRepository
from app.schemas.permission_schema import PermissionCreate, PermissionResponse
from app.utils.logger import get_logger


logger = get_logger("permission_router")


class PermissionRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/permissions", tags=["Permissions"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "",
            self.list_permissions,
            methods=["GET"],
            response_model=List[PermissionResponse],
        )
        self.router.add_api_route(
            "",
            self.create_permission,
            methods=["POST"],
            response_model=PermissionResponse,
        )

    async def list_permissions(
        self, 
        db: Session = Depends(get_db),
        current_user=Depends(require_roles([RoleID.ADMIN.value, RoleID.SUPERADMIN.value]))
    ):
        logger.info("Listing permissions")
        repo = PermissionRepository(db)
        permissions = repo.list()
        logger.info(f"Found {len(permissions)} permissions")
        return permissions

    async def create_permission(
        self,
        payload: PermissionCreate,
        db: Session = Depends(get_db),
        current_user=Depends(require_roles([RoleID.SUPERADMIN.value])),
    ):
        logger.info("Creating permission")
        repo = PermissionRepository(db)
        return repo.create(payload)


permission_router = PermissionRouter().router
