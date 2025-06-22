from typing import Generator, List

from app.core.auth import auth_manager, oauth2_scheme
from app.db.session import get_db
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User


__all__ = ["get_db", "oauth2_scheme", "get_uow", "require_roles"]

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session


class UoWDependency:
    """Object wrapper so we keep OO even for DI helpers."""

    def __call__(
        self, db: Session = Depends(get_db)
    ) -> Generator[UnitOfWork, None, None]:
        with UnitOfWork(db) as uow:
            yield uow


# Use either this implementation or the function below, but not both
# get_uow = UoWDependency()


def get_uow(db: Session = Depends(get_db)) -> UnitOfWork:
    """Get a Unit of Work instance for dependency injection."""
    return UnitOfWork(db)


def require_roles(allowed_roles: List[int]):
    """
    Dependency factory: only lets through users whose role_id is in allowed.
    Returns the current_user if check passes, otherwise raises 403.
    """

    async def _dependency(
        current_user: User = Depends(auth_manager.get_current_user),
    ) -> User:
        if current_user.role_id not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user

    return _dependency
