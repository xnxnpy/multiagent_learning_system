from app.services.auth_service import AuthService, auth_service
from app.services.user_service import UserService, user_service
from app.services.course_service import CourseService, course_service
from app.services.resource_review_service import ResourceReviewService, resource_review_service
from app.services.stats_service import StatsService, stats_service

__all__ = [
    "AuthService",
    "auth_service",
    "UserService",
    "user_service",
    "CourseService",
    "course_service",
    "ResourceReviewService",
    "resource_review_service",
    "StatsService",
    "stats_service"
]
