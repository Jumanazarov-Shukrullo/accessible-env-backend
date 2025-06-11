from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

from app.domain.repositories.assessment_comment_repository import AssessmentCommentRepository
from app.domain.repositories.assessment_detail_repository import AssessmentDetailRepository
from app.domain.repositories.assessment_image_repository import AssessmentImageRepository
from app.domain.repositories.assessment_repository import AssessmentRepository
from app.domain.repositories.assessment_set_repository import AssessmentSetRepository
from app.domain.repositories.category_repository import CategoryRepository
from app.domain.repositories.comment_repository import CommentRepository
from app.domain.repositories.criteria_repository import CriteriaRepository
from app.domain.repositories.favourite_repository import FavouriteRepository
from app.domain.repositories.geo_repository import CityRepository, DistrictRepository, RegionRepository
from app.domain.repositories.location_image_repository import LocationImageRepository
from app.domain.repositories.location_repository import LocationRepository
from app.domain.repositories.notification_repository import NotificationRepository
from app.domain.repositories.permission_repository import PermissionRepository
from app.domain.repositories.rating_repository import RatingRepository
from app.domain.repositories.review_repository import ReviewRepository
from app.domain.repositories.role_repository import RoleRepository
from app.domain.repositories.set_criteria_repository import SetCriteriaRepository
from app.domain.repositories.statistic_repository import StatisticRepository
from app.domain.repositories.user_repository import UserRepository

from abc import ABC, abstractmethod

class IUnitOfWork(ABC):
    @abstractmethod
    def __enter__(self): ...
    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb): ...
    @abstractmethod
    def commit(self): ...
    @abstractmethod
    def rollback(self): ...
    # plus abstract attributes: users, roles, etc.



class UnitOfWork(AbstractContextManager, IUnitOfWork):
    """Coordinates repositories & transaction boundaries."""

    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.permissions = PermissionRepository(db)
        self.locations = LocationRepository(db)
        self.assessment_sets = AssessmentSetRepository(db)
        self.assessments = AssessmentRepository(db)
        self.regions = RegionRepository(db)
        self.districts = DistrictRepository(db)
        self.cities = CityRepository(db)
        self.categories = CategoryRepository(db)
        self.reviews = ReviewRepository(db)
        self.ratings = RatingRepository(db)
        self.statistics = StatisticRepository(db)
        self.notifications = NotificationRepository(db)
        self.location_images = LocationImageRepository(db)
        self.criteria = CriteriaRepository(db)
        self.assessment_sets = AssessmentSetRepository(db)
        self.set_criteria = SetCriteriaRepository(db)
        self.assessment_details = AssessmentDetailRepository(db)
        self.assessment_images = AssessmentImageRepository(db)
        self.assessment_comments = AssessmentCommentRepository(db)
        self.comments = CommentRepository(db)
        self.favourites = FavouriteRepository(db)

    # ---- context‑manager API -----------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()

    # ---- public -------------------------------------------------------
    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
