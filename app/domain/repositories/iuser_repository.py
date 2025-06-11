from abc import ABC, abstractmethod
from typing import Optional
from app.domain.repositories.base import IRepository
from app.models.user_model import User


class IUserRepository(IRepository[User, str], ABC):
    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        pass

    @abstractmethod
    def create(self, user_data: dict) -> User:
        pass
