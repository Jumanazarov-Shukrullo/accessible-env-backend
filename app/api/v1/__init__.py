from fastapi import APIRouter
from app.api.v1.routers.category_router import category_router
from app.api.v1.routers.social_router import social_router
from app.api.v1.routers.geo_router import geo_router
from app.api.v1.routers.location_router import location_router
from app.api.v1.routers.notification_router import notification_router
from app.api.v1.routers.assessment_router import assessment_router
from app.api.v1.routers.assessment_detail_router import assessment_detail_router
from app.api.v1.routers.review_router import review_router
from app.api.v1.routers.rating_router import RatingRouter
from app.api.v1.routers.statistic_router import statistic_router
from app.api.v1.routers.statistics_router import statistics_router
from app.api.v1.routers.image_router import image_router
from app.api.v1.routers.user_router import user_router_instance
from app.api.v1.routers.assessment_set_router import assessment_set_router
from app.api.v1.routers.criteria_router import criteria_router
from app.api.v1.routers.role_router import role_router
from app.api.v1.routers.permission_router import permission_router

api_router = APIRouter()

api_router.include_router(user_router_instance.router, prefix="/users", tags=["Users"])
api_router.include_router(role_router, tags=["Roles"])
api_router.include_router(permission_router, tags=["Permissions"])
api_router.include_router(category_router)
api_router.include_router(social_router)
api_router.include_router(geo_router)
api_router.include_router(location_router)
api_router.include_router(notification_router)
api_router.include_router(assessment_router)
api_router.include_router(assessment_detail_router)
api_router.include_router(review_router)
api_router.include_router(RatingRouter().router)
api_router.include_router(statistic_router)
api_router.include_router(statistics_router)
api_router.include_router(image_router)
api_router.include_router(assessment_set_router)
api_router.include_router(criteria_router)
