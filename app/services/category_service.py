from fastapi import HTTPException

from app.domain.unit_of_work import UnitOfWork
from app.models.category_model import Category
from app.schemas.category_schema import CategorySchema
from app.utils.cache import cache


class CategoryService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def create(self, payload: CategorySchema.Create) -> Category:
        """Create a new category with optional parent relationship."""
        with self.uow:
            cat = Category(**payload.dict())
            self.uow.categories.add(cat)
            self.uow.commit()
            # Invalidate category cache
            cache.invalidate("categories")
            return cat

    @cache.cacheable(
        lambda self, category_id: f"categories:{category_id}", ttl=3600
    )
    def get(self, category_id: int) -> Category:
        """Get a specific category by ID."""
        category = self.uow.categories.get(category_id)
        if not category:
            raise HTTPException(404, "Category not found")
        return category

    def update(
        self, category_id: int, payload: CategorySchema.Update
    ) -> Category:
        """Update a category with the given data."""
        category = self.uow.categories.get(category_id)
        if not category:
            raise HTTPException(404, "Category not found")

        # Update fields
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(category, field, value)

        self.uow.commit()
        # Invalidate category caches
        cache.invalidate(f"categories:{category_id}")
        cache.invalidate("categories:tree")
        cache.invalidate("categories:list")
        cache.invalidate("categories:breadcrumb")
        return category

    def delete(self, category_id: int) -> None:
        """Delete a category and all its children."""
        category = self.get(category_id)
        self.uow.categories.delete(category)
        self.uow.commit()
        # Invalidate category caches
        cache.invalidate(f"categories:{category_id}")
        cache.invalidate("categories:tree")
        cache.invalidate("categories:list")
        cache.invalidate("categories:breadcrumb")

    @cache.cacheable(lambda self: "categories:tree", ttl=3600)
    def tree(self):
        """Return all root categories with their children as a hierarchical tree."""
        # First, get all categories (more efficient than multiple queries in
        # this case)
        all_categories = self.uow.categories.get_all()

        # Create serialization-friendly representation
        category_dict = {}
        for cat in all_categories:
            # Convert category to dictionary with only essential fields
            category_dict[cat.category_id] = {
                "category_id": cat.category_id,
                "category_name": cat.category_name,
                "slug": cat.slug,
                "description": cat.description,
                "parent_category_id": cat.parent_category_id,
                "icon": cat.icon or "Building2",  # Default icon if none set
                "children": [],  # Will be populated in next step
            }

        # Create a map of parent_id to children
        parent_map = {}
        for cat in all_categories:
            parent_id = cat.parent_category_id
            if parent_id not in parent_map:
                parent_map[parent_id] = []
            parent_map[parent_id].append(cat.category_id)

        # Populate children lists
        for cat_id, cat_data in category_dict.items():
            child_ids = parent_map.get(cat_id, [])
            for child_id in child_ids:
                cat_data["children"].append(category_dict[child_id])

        # Get root categories (those with parent_category_id = None)
        result = []
        for cat_id, cat_data in category_dict.items():
            if cat_data["parent_category_id"] is None:
                result.append(cat_data)

        return result

    @cache.cacheable(lambda self: "categories:list", ttl=3600)
    def list_all(self):
        """Return a flat list of all categories."""
        categories = self.uow.categories.get_all()
        # Convert SQLAlchemy models to dicts for better caching
        return [
            {
                "category_id": cat.category_id,
                "category_name": cat.category_name,
                "slug": cat.slug,
                "description": cat.description,
                "parent_category_id": cat.parent_category_id,
                "icon": cat.icon or "Building2",  # Default icon if none set
            }
            for cat in categories
        ]

    @cache.cacheable(
        lambda self, category_id: f"categories:breadcrumb:{category_id}",
        ttl=3600,
    )
    def breadcrumb(self, category_id: int):
        """Return the breadcrumb (ancestry) for a category."""
        all_categories = {
            cat.category_id: cat for cat in self.uow.categories.get_all()
        }
        path = []
        current = all_categories.get(category_id)
        while current:
            # Convert to dict to avoid SQLAlchemy serialization issues
            path.append(
                {
                    "category_id": current.category_id,
                    "category_name": current.category_name,
                    "slug": current.slug,
                    "description": current.description,
                    "parent_category_id": current.parent_category_id,
                    "icon": current.icon
                    or "Building2",  # Default icon if none set
                }
            )
            current = all_categories.get(current.parent_category_id)

        # Return reversed path (from root to current)
        return list(reversed(path))
