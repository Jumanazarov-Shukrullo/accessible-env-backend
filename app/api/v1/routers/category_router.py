from fastapi import APIRouter, Depends, status

from app.api.v1.dependencies import get_uow, require_roles
from app.core.auth import auth_manager
from app.core.constants import RoleID
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.category_schema import CategorySchema
from app.services.category_service import CategoryService
from app.utils.logger import get_logger

logger = get_logger("category_router")


class CategoryRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/categories", tags=["Categories"])
        self._register()

    def _register(self):
        self.router.post("/", response_model=CategorySchema.Out, status_code=201)(self._create_category)
        self.router.get("/", response_model=list[CategorySchema.Out])(self._list_tree)
        self.router.get("/flat", response_model=list[CategorySchema.Out])(self._list_all)
        self.router.get("/{category_id}", response_model=CategorySchema.Out)(self._get_category)
        self.router.put("/{category_id}", response_model=CategorySchema.Out)(self._update_category)
        self.router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)(self._delete_category)
        self.router.get("/{category_id}/breadcrumb", response_model=list[CategorySchema.Out])(self._breadcrumb)

    async def _create_category(
        self,
        payload: CategorySchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(require_roles([RoleID.SUPERADMIN.value, RoleID.ADMIN.value])),
    ):
        logger.info("Creating category")
        return CategoryService(uow).create(payload)

    async def _list_tree(self, uow: UnitOfWork = Depends(get_uow)):
        logger.info("Listing category tree")
        return CategoryService(uow).tree()

    async def _list_all(self, uow: UnitOfWork = Depends(get_uow)):
        logger.info("Listing all categories")
        return CategoryService(uow).list_all()

    async def _get_category(self, category_id: int, uow: UnitOfWork = Depends(get_uow)):
        logger.info(f"Getting category {category_id}")
        return CategoryService(uow).get(category_id)

    async def _update_category(
        self,
        category_id: int,
        payload: CategorySchema.Update,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(require_roles([RoleID.SUPERADMIN.value, RoleID.ADMIN.value])),
    ):
        logger.info(f"Updating category {category_id}")
        return CategoryService(uow).update(category_id, payload)

    async def _delete_category(
        self,
        category_id: int,
        uow: UnitOfWork = Depends(get_uow),
        _: User = Depends(require_roles([RoleID.SUPERADMIN.value, RoleID.ADMIN.value])),
    ):
        logger.info(f"Deleting category {category_id}")
        CategoryService(uow).delete(category_id)
        return None

    async def _breadcrumb(self, category_id: int, uow: UnitOfWork = Depends(get_uow)):
        logger.info(f"Getting breadcrumb for category {category_id}")
        return CategoryService(uow).breadcrumb(category_id)


category_router = CategoryRouter().router
