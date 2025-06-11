from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "category"
    category_id: Mapped[int] = mapped_column(primary_key=True)
    category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(100), unique=True)
    description: Mapped[str | None]
    icon: Mapped[str | None] = mapped_column(String(50), default="Building2")  # Lucide icon name

    parent_category_id: Mapped[int | None] = mapped_column(ForeignKey("category.category_id"))
    parent: Mapped["Category"] = relationship(remote_side="Category.category_id", back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent", cascade="all,delete")
