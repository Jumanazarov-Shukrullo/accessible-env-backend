from typing import List, Optional
import time
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import auth_manager
from app.core.constants import RoleID
from app.db.session import get_db
from app.schemas.permission_schema import PermissionResponse
from app.schemas.role_schema import RoleCreate, RoleResponse, RoleUpdate
from app.services.role_service import RoleService
from app.utils.logger import get_logger
from app.api.v1.dependencies import get_uow
from app.domain.unit_of_work import UnitOfWork

logger = get_logger("role_router")

# Cache for role service instances to reuse cached data
_role_service_cache = {}

def get_cached_role_service(db: Session) -> RoleService:
    """Get a cached role service to reuse data across requests"""
    db_id = id(db)
    if db_id not in _role_service_cache:
        _role_service_cache[db_id] = RoleService(db)
    return _role_service_cache[db_id]

class RoleRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/roles", tags=["Roles"])
        self.register_routes()

    def register_routes(self):
        # List & CRUD endpoints
        self.router.add_api_route("", self.list_roles, methods=["GET"], response_model=List[RoleResponse])
        self.router.add_api_route("", self.create_role, methods=["POST"], response_model=RoleResponse)
        
        # Permission management routes
        self.router.add_api_route("/{role_id}/permissions", self.list_role_permissions, methods=["GET"])
        self.router.add_api_route("/{role_id}/permissions/{permission_id}", self.grant_permission, methods=["POST"])
        self.router.add_api_route("/{role_id}/permissions/{permission_id}", self.revoke_permission, methods=["DELETE"])
        
        # Permission CRUD endpoints
        self.router.add_api_route("/permissions", self.create_permission, methods=["POST"], response_model=dict)
        self.router.add_api_route("/permissions/{permission_id}", self.update_permission, methods=["PUT"], response_model=dict)
        self.router.add_api_route("/permissions/{permission_id}", self.delete_permission, methods=["DELETE"], status_code=204)
        
        # User assignment routes
        self.router.add_api_route("/{role_id}/users", self.get_role_users, methods=["GET"])
        
        # Statistics route
        self.router.add_api_route("/statistics", self.get_statistics, methods=["GET"])
        
        # Single role routes (must be last)
        self.router.add_api_route("/{role_id}", self.get_role, methods=["GET"])
        self.router.add_api_route("/{role_id}", self.update_role, methods=["PUT"])
        self.router.add_api_route("/{role_id}", self.delete_role, methods=["DELETE"])

    async def list_roles(self, db: Session = Depends(get_db)):
        start_time = time.time()
        logger.info("API: Starting list_roles")
        
        result = get_cached_role_service(db).list_roles()
        
        end_time = time.time()
        logger.info(f"API: list_roles completed in {(end_time - start_time) * 1000:.2f}ms")
        return result

    async def create_role(
        self, payload: RoleCreate, db: Session = Depends(get_db), current_user=Depends(auth_manager.get_current_user)
    ):
        if current_user.role_id != RoleID.SUPERADMIN:
            raise HTTPException(403, "Only superadmins can create roles")
        logger.info("Creating role")
        return RoleService(db).create_role(payload)

    async def get_role(self, role_id: int, db: Session = Depends(get_db)):
        logger.info(f"Getting role with id: {role_id}")
        return RoleService(db).get_role(role_id)

    async def update_role(
        self,
        role_id: int,
        payload: RoleUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(auth_manager.get_current_user),
    ):
        if current_user.role_id != RoleID.SUPERADMIN:
            raise HTTPException(403, "Only superadmins can modify roles")
        logger.info(f"Updating role with id: {role_id}")
        return RoleService(db).update_role(role_id, payload)

    async def delete_role(
        self, role_id: int, db: Session = Depends(get_db), current_user=Depends(auth_manager.get_current_user)
    ):
        if current_user.role_id != RoleID.SUPERADMIN:
            raise HTTPException(403, "Only superadmins can delete roles")
        logger.info(f"Deleting role with id: {role_id}")
        RoleService(db).delete_role(role_id)

    async def assign_permission(
        self,
        role_id: int,
        permission_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(auth_manager.get_current_user),
    ):
        if current_user.role_id != RoleID.SUPERADMIN:
            raise HTTPException(403, "Only superadmins can assign permissions")
        logger.info(f"Assigning permission with id: {permission_id} to role with id: {role_id}")
        return RoleService(db).assign_permission_to_role(role_id, permission_id)

    async def get_role_users(
        self,
        role_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(auth_manager.get_current_user),
    ):
        """Get all users assigned to a specific role"""
        logger.info(f"Getting users for role {role_id}")
        
        try:
            # Get users for the role using the service
            service = get_cached_role_service(db)
            users = service.get_users_by_role(role_id)
            
            user_list = []
            for user in users:
                # Access profile data from normalized structure
                full_name = None
                if user.profile:
                    if user.profile.first_name and user.profile.surname:
                        full_name = f"{user.profile.first_name} {user.profile.surname}".strip()
                
                user_data = {
                    "user_id": str(user.user_id),
                    "username": user.username,
                    "full_name": full_name or user.username,
                    "email": user.email,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat(),
                    "last_login_at": user.security.last_login_at.isoformat() if user.security and user.security.last_login_at else None
                }
                user_list.append(user_data)
                logger.info(f"User data: {user_data}")
            
            result = {
                "items": user_list,
                "total": len(user_list)
            }
            logger.info(f"Returning result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting users for role {role_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="Failed to get role users")

    async def get_statistics(
        self, 
        _optimize: Optional[bool] = Query(None, description="Hint for backend optimization"),
        db: Session = Depends(get_db)
    ):
        start_time = time.time()
        logger.info(f"API: Getting role statistics (optimize={_optimize})")
        
        try:
            service = get_cached_role_service(db)
            result = service.get_statistics()
            
            end_time = time.time()
            logger.info(f"API: get_statistics completed in {(end_time - start_time) * 1000:.2f}ms")
            return result
        except Exception as e:
            logger.error(f"Error getting role statistics: {e}")
            # Return safe default statistics
            return {
                "total_roles": 0,
                "system_roles": 0,
                "custom_roles": 0,
                "most_assigned_role": None,
                "least_assigned_role": None,
                "role_distribution": []
            }

    async def create_permission(
        self,
        permission: dict,
        db: Session = Depends(get_db),
        current_user=Depends(auth_manager.get_current_user),
    ):
        """Create a new permission"""
        logger.info(f"Creating new permission: {permission}")
        
        try:
            from app.models.permission_model import Permission
            
            # Check if permission already exists
            existing = db.query(Permission).filter(
                Permission.permission_name == permission.get("permission_name")
            ).first()
            
            if existing:
                raise HTTPException(status_code=400, detail="Permission already exists")
            
            new_permission = Permission(
                permission_name=permission["permission_name"],
                description=permission.get("description", ""),
                resource=permission.get("resource", ""),
                action=permission.get("action", "")
            )
            
            db.add(new_permission)
            db.commit()
            db.refresh(new_permission)
            
            return {
                "permission_id": new_permission.permission_id,
                "permission_name": new_permission.permission_name,
                "description": new_permission.description,
                "resource": new_permission.resource,
                "action": new_permission.action,
                "created_at": new_permission.created_at.isoformat(),
                "updated_at": new_permission.updated_at.isoformat() if new_permission.updated_at else None
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating permission: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create permission")
    
    async def update_permission(
        self,
        permission_id: int,
        permission: dict,
        db: Session = Depends(get_db),
        current_user=Depends(auth_manager.get_current_user),
    ):
        """Update an existing permission"""
        logger.info(f"Updating permission {permission_id}: {permission}")
        
        try:
            from app.models.permission_model import Permission
            
            existing_permission = db.query(Permission).filter(
                Permission.permission_id == permission_id
            ).first()
            
            if not existing_permission:
                raise HTTPException(status_code=404, detail="Permission not found")
            
            # Update fields
            if "permission_name" in permission:
                existing_permission.permission_name = permission["permission_name"]
            if "description" in permission:
                existing_permission.description = permission["description"]
            if "resource" in permission:
                existing_permission.resource = permission["resource"]
            if "action" in permission:
                existing_permission.action = permission["action"]
            
            db.commit()
            db.refresh(existing_permission)
            
            return {
                "permission_id": existing_permission.permission_id,
                "permission_name": existing_permission.permission_name,
                "description": existing_permission.description,
                "resource": existing_permission.resource,
                "action": existing_permission.action,
                "created_at": existing_permission.created_at.isoformat(),
                "updated_at": existing_permission.updated_at.isoformat() if existing_permission.updated_at else None
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating permission: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update permission")
    
    async def delete_permission(
        self,
        permission_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(auth_manager.get_current_user),
    ):
        """Delete a permission"""
        logger.info(f"Deleting permission {permission_id}")
        
        try:
            from app.models.permission_model import Permission
            from app.models.role_permission_model import RolePermission
            
            permission = db.query(Permission).filter(
                Permission.permission_id == permission_id
            ).first()
            
            if not permission:
                raise HTTPException(status_code=404, detail="Permission not found")
            
            # Remove from all roles first
            db.query(RolePermission).filter(
                RolePermission.permission_id == permission_id
            ).delete()
            
            # Delete the permission
            db.delete(permission)
            db.commit()
            
            return {"message": "Permission deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting permission: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to delete permission")

    async def list_role_permissions(
        self,
        role_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(auth_manager.get_current_user),
    ):
        """Get all permissions for a specific role"""
        logger.info(f"Getting permissions for role {role_id}")
        
        try:
            # Debug: Check role existence
            from app.models.role_model import Role
            role = db.query(Role).filter(Role.role_id == role_id).first()
            if not role:
                logger.error(f"Role {role_id} not found")
                return []
            
            logger.info(f"Found role: {role.role_name}")
            
            # Use the optimized service method
            role_service = get_cached_role_service(db)
            permissions = role_service._get_permissions_for_role(role_id)
            
            logger.info(f"Found {len(permissions)} permissions for role {role_id}")
            logger.info(f"Permissions: {[p['permission_name'] for p in permissions]}")
            
            return permissions
        except Exception as e:
            logger.error(f"Error getting permissions for role {role_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="Failed to get role permissions")

    async def grant_permission(
        self,
        role_id: int,
        permission_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(auth_manager.get_current_user),
    ):
        """Grant a permission to a role"""
        logger.info(f"Granting permission {permission_id} to role {role_id}")
        
        try:
            role_service = RoleService(db)
            return role_service.assign_permission_to_role(role_id, permission_id)
        except Exception as e:
            logger.error(f"Error granting permission: {e}")
            raise HTTPException(status_code=500, detail="Failed to grant permission")

    async def revoke_permission(
        self,
        role_id: int,
        permission_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(auth_manager.get_current_user),
    ):
        """Revoke a permission from a role"""
        logger.info(f"Revoking permission {permission_id} from role {role_id}")
        
        try:
            role_service = RoleService(db)
            role_service.revoke_permission_from_role(role_id, permission_id)
            return {"message": "Permission revoked successfully"}
        except Exception as e:
            logger.error(f"Error revoking permission: {e}")
            raise HTTPException(status_code=500, detail="Failed to revoke permission")


role_router = RoleRouter().router
