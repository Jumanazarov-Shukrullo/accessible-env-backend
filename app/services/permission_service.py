from app.core.constants import RoleID
from app.models.user_model import User
from fastapi import HTTPException, status
from app.schemas.user_schema import InviteCreate


def only_invite_admin_or_superadmin(payload: InviteCreate):
    if payload.role_id not in (RoleID.ADMIN.value, RoleID.SUPERADMIN.value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only invite admins or superadmins")


def can_invite_role(inviter: User, target_role_id: int):
    if target_role_id == RoleID.SUPERADMIN.value and inviter.role_id != RoleID.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only superadmins can invite other superadmins"
        )
    return True


def can_ban_user(actor: User, target: User):
    if target.role_id == RoleID.SUPERADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot ban a superadmin")
    if target.user_id == actor.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot ban yourself")
    return True


def can_change_role(actor: User, target: User, new_role: int):
    if target.role_id == RoleID.SUPERADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change role of a superadmin")
    if target.user_id == actor.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot change your own role")
    if new_role == RoleID.SUPERADMIN.value and actor.role_id != RoleID.SUPERADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only superadmins can promote to superadmin")
    return True
