from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_uow
from app.core.auth import auth_manager
from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User
from app.schemas.social_schema import CommentSchema, FavouriteSchema
from app.services.social_service import SocialService
from app.utils.logger import get_logger


logger = get_logger("social_router")


class SocialRouter:
    def __init__(self):
        self.router = APIRouter(
            prefix="/social", tags=["Comments & Favourites"]
        )
        self._register()

    def _register(self):
        # Comments
        self.router.post(
            "/comments", response_model=CommentSchema.Out, status_code=201
        )(self._add_comment)
        self.router.get("/comments", response_model=list[CommentSchema.Out])(
            self._get_thread
        )

        # Favourites
        self.router.post("/favourites/toggle", status_code=200)(
            self._toggle_favourite
        )
        self.router.get(
            "/favourites", response_model=list[FavouriteSchema.Out]
        )(self._list_favs)

    # ------------ comments -------------------------------------------
    async def _add_comment(
        self,
        payload: CommentSchema.Create,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Adding comment")
        return SocialService(uow).add_comment(payload, current)

    async def _get_thread(self, uow: UnitOfWork = Depends(get_uow)):
        logger.info("Getting thread")
        return SocialService(uow).thread()

    # ------------ favourites -----------------------------------------
    async def _toggle_favourite(
        self,
        payload: FavouriteSchema.Toggle,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Toggling favourite")
        added = SocialService(uow).toggle_favourite(payload, current)
        return {"is_favourite": added}

    async def _list_favs(
        self,
        uow: UnitOfWork = Depends(get_uow),
        current: User = Depends(auth_manager.get_current_user),
    ):
        logger.info("Listing favourites")
        return SocialService(uow).list_user_favs(current.user_id)


social_router = SocialRouter().router
