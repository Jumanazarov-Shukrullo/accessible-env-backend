from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.favourite_model import Favourite


class FavouriteRepository(SQLAlchemyRepository[Favourite, int]):
    def __init__(self, db: Session):
        super().__init__(Favourite, db)

    def get_user_fav(
        self, user_id: UUID, location_id: UUID
    ) -> Favourite | None:
        stmt = select(Favourite).where(
            Favourite.user_id == str(user_id),
            Favourite.location_id == str(location_id),
        )
        return self.db.scalar(stmt)

    def list(self, filter_by: Dict[str, Any] = None) -> List[Favourite]:
        """List favourites with optional filtering"""
        query = self.db.query(Favourite)

        if filter_by:
            for key, value in filter_by.items():
                if hasattr(Favourite, key):
                    query = query.filter(getattr(Favourite, key) == value)

        return query.all()
