"""Shared FastAPI dependencies for route modules."""
from app.database import get_db  # re-exported for convenience
from app.core.security import CurrentUser, Roles, get_current_user, require_roles

__all__ = ["get_db", "CurrentUser", "Roles", "get_current_user", "require_roles"]
