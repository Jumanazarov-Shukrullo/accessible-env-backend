from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.category_model import Category


class CategoryRepository(SQLAlchemyRepository[Category, int]):
    def __init__(self, db: Session):
        super().__init__(Category, db)

    def children_of(self, parent_id: int):
        return (
            self.db.query(Category)
            .filter(Category.parent_category_id == parent_id)
            .all()
        )
