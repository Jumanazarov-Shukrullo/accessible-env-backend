import logging
import time
from typing import Dict, List

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.repositories.permission_repository import PermissionRepository
from app.domain.repositories.role_repository import RoleRepository
from app.models.permission_model import Permission
from app.models.role_permission_model import RolePermission
from app.models.user_model import User
from app.schemas.permission_schema import PermissionResponse
from app.schemas.role_schema import RoleCreate, RoleResponse, RoleUpdate


logger = logging.getLogger(__name__)


class RoleService:
    def __init__(self, db: Session):
        self.repo = RoleRepository(db)
        self.perm_repo = PermissionRepository(db)
        self.db = db
        self._permissions_cache = {}  # Cache for permissions
        self._user_counts_cache = {}  # Cache for user counts

    def _get_all_role_permissions_bulk(self) -> Dict[int, List[dict]]:
        """Load ALL role permissions in a single optimized query"""
        try:
            start_time = time.time()
            logger.info("Loading ALL role permissions in bulk")

            # Single query to get all role-permission mappings with permission
            # details
            query_result = (
                self.db.query(
                    RolePermission.role_id,
                    Permission.permission_id,
                    Permission.permission_name,
                    Permission.description,
                    Permission.resource,
                    Permission.action,
                )
                .join(
                    Permission,
                    Permission.permission_id == RolePermission.permission_id,
                )
                .all()
            )

            # Group by role_id
            role_permissions = {}
            for row in query_result:
                role_id = row.role_id
                if role_id not in role_permissions:
                    role_permissions[role_id] = []

                role_permissions[role_id].append(
                    {
                        "permission_id": row.permission_id,
                        "permission_name": row.permission_name,
                        "description": row.description,
                        "resource": row.resource,
                        "action": row.action,
                    }
                )

            end_time = time.time()
            logger.info(
                f"Bulk loaded permissions for {
                    len(role_permissions)} roles in {
                    (
                        end_time -
                        start_time) *
                    1000:.2f}ms")

            # Cache the results
            self._permissions_cache = role_permissions
            return role_permissions

        except Exception as e:
            logger.error(f"Error bulk loading permissions: {e}")
            return {}

    def _get_all_user_counts_bulk(self) -> Dict[int, int]:
        """Load ALL user counts in a single query"""
        try:
            start_time = time.time()
            logger.info("Loading ALL user counts in bulk")

            # Single query to count users per role
            user_counts = (
                self.db.query(
                    User.role_id, func.count(User.user_id).label("user_count")
                )
                .group_by(User.role_id)
                .all()
            )

            # Convert to dict
            counts_dict = {row.role_id: row.user_count for row in user_counts}

            end_time = time.time()
            logger.info(
                f"Bulk loaded user counts in {(end_time - start_time) * 1000:.2f}ms"
            )

            # Cache the results
            self._user_counts_cache = counts_dict
            return counts_dict

        except Exception as e:
            logger.error(f"Error bulk loading user counts: {e}")
            return {}

    def _get_user_count_for_role(self, role_id: int) -> int:
        """Get cached user count for a specific role"""
        if not self._user_counts_cache:
            self._get_all_user_counts_bulk()
        return self._user_counts_cache.get(role_id, 0)

    def _get_permissions_for_role(self, role_id: int) -> List[dict]:
        """Get cached permissions for a specific role"""
        if not self._permissions_cache:
            self._get_all_role_permissions_bulk()
        return self._permissions_cache.get(role_id, [])

    def create_role(self, data: RoleCreate) -> RoleResponse:
        return self.repo.create(data.dict())

    def list_roles(self) -> List[RoleResponse]:
        start_time = time.time()
        logger.info("Starting optimized list_roles")

        # Load base roles
        roles = self.repo.list()

        # Bulk load all permissions and user counts in parallel
        self._get_all_role_permissions_bulk()
        self._get_all_user_counts_bulk()

        # Convert Role objects to RoleResponse objects with cached data
        role_responses = []
        for role in roles:
            user_count = self._get_user_count_for_role(role.role_id)
            permissions = self._get_permissions_for_role(role.role_id)

            role_response = RoleResponse(
                role_id=role.role_id,
                role_name=role.role_name,
                description=role.description,
                level=role.level,
                is_system_role=role.is_system_role,
                user_count=user_count,
                created_at=role.created_at,
                updated_at=role.updated_at,
                permissions=permissions,
            )
            role_responses.append(role_response)

        end_time = time.time()
        logger.info(
            f"Optimized list_roles completed in {
                (
                    end_time -
                    start_time) *
                1000:.2f}ms for {
                len(role_responses)} roles")
        return role_responses

    def get_role(self, role_id: int) -> RoleResponse:
        role = self.repo.get(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        user_count = self._get_user_count_for_role(role.role_id)
        permissions = self._get_permissions_for_role(role.role_id)

        # Convert to RoleResponse
        return RoleResponse(
            role_id=role.role_id,
            role_name=role.role_name,
            description=role.description,
            level=role.level,
            is_system_role=role.is_system_role,
            user_count=user_count,
            created_at=role.created_at,
            updated_at=role.updated_at,
            permissions=permissions,
        )

    def update_role(self, role_id: int, data: RoleUpdate) -> RoleResponse:
        role = self.repo.get(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        updated_role = self.repo.update(role, data.dict(exclude_unset=True))

        user_count = self._get_user_count_for_role(updated_role.role_id)
        permissions = self._get_permissions_for_role(updated_role.role_id)

        # Convert to RoleResponse
        return RoleResponse(
            role_id=updated_role.role_id,
            role_name=updated_role.role_name,
            description=updated_role.description,
            level=updated_role.level,
            is_system_role=updated_role.is_system_role,
            user_count=user_count,
            created_at=updated_role.created_at,
            updated_at=updated_role.updated_at,
            permissions=permissions,
        )

    def delete_role(self, role_id: int) -> None:
        role = self.repo.get(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        self.repo.delete(role)

    def assign_permission_to_role(
        self, role_id: int, permission_id: int
    ) -> PermissionResponse:
        role = self.repo.get(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        permission = self.perm_repo.get(permission_id)
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")
        return self.repo.assign_permission(role, permission)

    def revoke_permission_from_role(
        self, role_id: int, permission_id: int
    ) -> None:
        role = self.repo.get(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        permission = self.perm_repo.get(permission_id)
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")
        self.repo.revoke_permission(role, permission)

    def get_statistics(self) -> dict:
        """Get role statistics for the admin dashboard."""
        try:
            start_time = time.time()
            logger.info("Starting optimized get_statistics method")

            # Use cached data if available, otherwise load fresh
            if not self._permissions_cache or not self._user_counts_cache:
                all_roles = self.list_roles()  # This will populate caches
            else:
                # Use cached data for ultra-fast statistics
                logger.info("Using cached data for statistics")
                roles = self.repo.list()
                all_roles = []
                for role in roles:
                    user_count = self._get_user_count_for_role(role.role_id)
                    permissions = self._get_permissions_for_role(role.role_id)

                    role_response = RoleResponse(
                        role_id=role.role_id,
                        role_name=role.role_name,
                        description=role.description,
                        level=role.level,
                        is_system_role=role.is_system_role,
                        user_count=user_count,
                        created_at=role.created_at,
                        updated_at=role.updated_at,
                        permissions=permissions,
                    )
                    all_roles.append(role_response)

            logger.info(f"Found {len(all_roles)} roles")

            total_roles = len(all_roles)
            system_roles = len([r for r in all_roles if r.is_system_role])
            custom_roles = total_roles - system_roles

            # Find most and least assigned roles based on user count
            most_assigned_role = None
            least_assigned_role = None

            if all_roles:
                sorted_roles = sorted(
                    all_roles, key=lambda r: r.user_count, reverse=True
                )
                most_assigned = sorted_roles[0]
                least_assigned = sorted_roles[-1]

                most_assigned_role = {
                    "role_id": most_assigned.role_id,
                    "role_name": most_assigned.role_name,
                    "description": most_assigned.description,
                    "level": most_assigned.level,
                    "is_system_role": most_assigned.is_system_role,
                }
                least_assigned_role = {
                    "role_id": least_assigned.role_id,
                    "role_name": least_assigned.role_name,
                    "description": least_assigned.description,
                    "level": least_assigned.level,
                    "is_system_role": least_assigned.is_system_role,
                }

            # Calculate distribution percentages
            total_users = sum(role.user_count for role in all_roles)
            role_distribution = []
            for role in all_roles:
                percentage = (
                    (role.user_count / total_users * 100)
                    if total_users > 0
                    else 0
                )
                role_distribution.append(
                    {
                        "role_id": role.role_id,
                        "role_name": role.role_name,
                        "user_count": role.user_count,
                        "percentage": percentage,
                    }
                )

            result = {
                "total_roles": total_roles,
                "system_roles": system_roles,
                "custom_roles": custom_roles,
                "most_assigned_role": most_assigned_role,
                "least_assigned_role": least_assigned_role,
                "role_distribution": role_distribution,
            }

            end_time = time.time()
            logger.info(
                f"Optimized statistics completed in {(end_time - start_time) * 1000:.2f}ms"
            )
            logger.info(f"Successfully generated statistics: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in get_statistics: {str(e)}")
            logger.error(f"Exception type: {type(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return safe default values
            return {
                "total_roles": 0,
                "system_roles": 0,
                "custom_roles": 0,
                "most_assigned_role": None,
                "least_assigned_role": None,
                "role_distribution": [],
            }

    def get_users_by_role(self, role_id: int) -> List[User]:
        """Get all users assigned to a specific role"""
        logger.info(f"Getting users for role {role_id}")
        
        try:
            from sqlalchemy.orm import joinedload
            
            # Query users with the specified role, including their profile and security data
            users = (
                self.db.query(User)
                .options(
                    joinedload(User.profile),
                    joinedload(User.security),
                    joinedload(User.role)
                )
                .filter(User.role_id == role_id)
                .order_by(User.created_at.desc())
                .all()
            )
            
            logger.info(f"Found {len(users)} users with role {role_id}")
            return users
            
        except Exception as e:
            logger.error(f"Error getting users for role {role_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to get users for role {role_id}"
            )
