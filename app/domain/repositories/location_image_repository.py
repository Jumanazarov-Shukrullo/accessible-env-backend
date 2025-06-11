from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.location_images_model import LocationImage


class LocationImageRepository(SQLAlchemyRepository[LocationImage, int]):
    """CRUD + convenience helpers for LocationImage rows."""

    def __init__(self, db: Session):
        super().__init__(LocationImage, db)

    # ---------------------------------------------------------------
    def list_for_location(self, loc_id: UUID):
        return (
            self.db.query(LocationImage)
            .filter(LocationImage.location_id == str(loc_id))
            .order_by(LocationImage.position)
            .all()
        )

    def get_by_object_name_and_loc(self, loc_id: str, object_name: str) -> Optional[LocationImage]:
        return self.db.query(LocationImage).filter_by(location_id=loc_id, image_url=object_name).first()

    def delete(self, image: LocationImage):
        self.db.delete(image)
        self.db.commit()
