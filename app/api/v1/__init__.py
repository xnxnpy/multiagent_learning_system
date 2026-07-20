from fastapi import APIRouter
from app.api.v1 import auth, admin, student, tutor, tutor_stream, teacher, notification, profile_chat, showcase

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(student.router)
api_router.include_router(tutor.router)
api_router.include_router(tutor_stream.router)
api_router.include_router(teacher.router)
api_router.include_router(notification.router)
api_router.include_router(profile_chat.router)
api_router.include_router(showcase.router)
