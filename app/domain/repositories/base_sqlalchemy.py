from __future__ import annotations

from typing import Generic, Sequence, Type

from sqlalchemy.orm import Session

from app.domain.repositories.base import ID, IRepository, T


class SQLAlchemyRepository(Generic[T, ID], IRepository[T, ID]):
    """Generic SQLAlchemy repository with basic CRUD."""

    def __init__(self, model: Type[T], db: Session):
        self.model = model
        self.db = db

    # ----- CRUD --------------------------------------------------------
    def add(self, obj: T) -> T:
        self.db.add(obj)
        return obj

    def get(self, id_: ID) -> T | None:
        return self.db.get(self.model, id_)

    def get_all(self, offset: int = 0, limit: int = 100) -> Sequence[T]:
        stmt = self.db.query(self.model).offset(offset).limit(limit)
        return stmt.all()

    def delete(self, obj: T) -> None:
        self.db.delete(obj)

    def flush(self) -> None:
        self.db.flush()
