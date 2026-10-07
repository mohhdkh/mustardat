# API Routes
from app.api.routes.users import router as users_router
from app.api.routes.auth import router as auth_router
from app.api.routes.items import router as items_router
from app.api.routes.matches import router as matches_router
from app.api.routes.notifications import router as notifications_router

__all__ = [
    "users_router",
    "auth_router",
    "items_router",
    "matches_router",
    "notifications_router",
]
