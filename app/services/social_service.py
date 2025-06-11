from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import ProgrammingError

from app.domain.unit_of_work import UnitOfWork
from app.models.comment_model import Comment
from app.models.favourite_model import Favourite
from app.models.user_model import User
from app.schemas.social_schema import CommentSchema, FavouriteSchema
from app.utils.cache import cache


class SocialService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # ---------------- Comments ---------------------------------------
    def add_comment(self, payload: CommentSchema.Create, user: User) -> Comment:
        with self.uow:
            com = Comment(**payload.dict(), user_id=str(user.user_id))
            self.uow.comments.add(com)
            self.uow.commit()
            cache.invalidate("comment_thread")  # invalidate cached thread
            return com

    @cache.cacheable(lambda *_, **__: "comment_thread")
    def thread(self):
        try:
            return self.uow.comments.thread()
        except ProgrammingError:
            # Comment table doesn't exist yet, return empty list
            return []

    # ---------------- Favourites -------------------------------------
    def toggle_favourite(self, payload: FavouriteSchema.Toggle, user: User) -> bool:
        with self.uow:
            fav = self.uow.favourites.get_user_fav(user.user_id, payload.location_id)
            if fav:
                self.uow.favourites.delete(fav)
                self.uow.commit()
                return False
            new_fav = Favourite(user_id=str(user.user_id), location_id=str(payload.location_id))
            self.uow.favourites.add(new_fav)
            self.uow.commit()
            return True

    def list_user_favs(self, user_id: UUID):
        return self.uow.favourites.list(filter_by=dict(user_id=str(user_id)))
