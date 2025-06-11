from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, Sequence, TypeVar


T = TypeVar("T")  # SQLAlchemy model type
ID = TypeVar("ID")  # primary‑key type


class IRepository(Generic[T, ID], ABC):
    """Generic repository interface (CRUD+)."""

    @abstractmethod
    def add(self, obj: T) -> T: ...

    @abstractmethod
    def get(self, id_: ID) -> T | None: ...

    @abstractmethod
    def get_all(self, *, offset: int = 0, limit: int = 100) -> Sequence[T]: ...

    @abstractmethod
    def delete(self, obj: T) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...
