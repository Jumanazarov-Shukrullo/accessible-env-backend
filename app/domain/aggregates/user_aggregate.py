from fastapi import HTTPException, status

from app.models.user_model import User


class UserAggregate:
    def __init__(self, user: User) -> None:
        self.user = user

    def promote_to_admin(self) -> None:
        # Example: role_id: 1 = superadmin, 2 = admin, 3 = user.
        if self.user.role_id == 1:
            # Already superadmin; no promotion needed.
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already superadmin")
        self.user.role_id = 2

    def demote_to_user(self) -> None:
        if self.user.role_id == 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot demote a superadmin")
        self.user.role_id = 3

    def ban(self) -> None:
        self.user.is_active = False
