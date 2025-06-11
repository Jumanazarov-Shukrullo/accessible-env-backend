from sqlalchemy.orm import Session

from app.domain.repositories.base_sqlalchemy import SQLAlchemyRepository
from app.models.city_model import City
from app.models.district_model import District
from app.models.region_model import Region


class RegionRepository(SQLAlchemyRepository[Region, int]):
    def __init__(self, db: Session):
        super().__init__(Region, db)

    def get_paginated(self, limit: int, offset: int):
        query = self.db.query(Region)
        total = query.count()
        items = query.order_by(Region.region_id).offset(offset).limit(limit).all()
        return items, total


class DistrictRepository(SQLAlchemyRepository[District, int]):
    def __init__(self, db: Session):
        super().__init__(District, db)

    def in_region(self, region_id: int):
        return self.db.query(District).filter(District.region_id == region_id).all()

    def get_paginated(self, limit: int, offset: int):
        query = self.db.query(District)
        total = query.count()
        items = query.order_by(District.district_id).offset(offset).limit(limit).all()
        return items, total


class CityRepository(SQLAlchemyRepository[City, int]):
    def __init__(self, db: Session):
        super().__init__(City, db)

    def in_district(self, district_id: int):
        return self.db.query(City).filter(City.district_id == district_id).all()

    def get_paginated(self, limit: int, offset: int):
        query = self.db.query(City)
        total = query.count()
        items = query.order_by(City.city_id).offset(offset).limit(limit).all()
        return items, total
