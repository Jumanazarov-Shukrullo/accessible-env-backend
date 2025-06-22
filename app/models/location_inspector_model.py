import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from .location_model import Location  # noqa
    from .user_model import User  # noqa


class LocationInspector(Base):
    __tablename__ = "location_inspectors"
    __table_args__ = {"extend_existing": True}

    location_id: Mapped[str] = mapped_column(
        ForeignKey("locations.location_id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    assigned_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=dt.datetime.utcnow
    )

    location: Mapped["Location"] = relationship(back_populates="inspectors")
    user: Mapped["User"] = relationship(lazy="joined")

    @hybrid_property
    def username(self):
        return self.user.username if self.user else None

    @hybrid_property
    def first_name(self):
        return (
            self.user.profile.first_name
            if self.user and self.user.profile
            else None
        )

    @hybrid_property
    def surname(self):
        return (
            self.user.profile.surname
            if self.user and self.user.profile
            else None
        )

    @hybrid_property
    def middle_name(self):
        return (
            self.user.profile.middle_name
            if self.user and self.user.profile
            else None
        )

    @hybrid_property
    def email(self):
        return self.user.email if self.user else None

    # Potentially, if full_name is still needed directly on the ORM model for other reasons,
    # it could also be a hybrid_property, though InspectorOut will now compute it.
    # @hybrid_property
    # def full_name(self):
    #     if self.user and self.user.first_name and self.user.surname:
    #         middle = f" {self.user.middle_name} " if self.user.middle_name else " "
    #         return f"{self.user.first_name}{middle}{self.user.surname}".replace("  ", " ").strip()
    #     return None
