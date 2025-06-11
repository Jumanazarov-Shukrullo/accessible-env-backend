import datetime as dt
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CommentSchema:
    class Create(BaseModel):
        body: str
        parent_comment_id: Optional[int] = None

    class Out(Create):
        comment_id: int
        user_id: UUID
        created_at: dt.datetime
        is_edited: bool
        children: List["CommentSchema.Out"] = []

        model_config = ConfigDict(from_attributes=True)


CommentSchema.Out.update_forward_refs()


class FavouriteSchema:
    class Toggle(BaseModel):
        location_id: UUID

    class Out(BaseModel):
        favorite_id: int
        location_id: UUID
        created_at: dt.datetime

        model_config = ConfigDict(from_attributes=True)


class SocialResponse(BaseModel):
    # ... fields ...
    model_config = ConfigDict(from_attributes=True)
