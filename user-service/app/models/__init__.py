"""User Service ORM models — imported here so Base.metadata (used by both
`create_all` at startup and Alembic autogeneration) is aware of every table.
"""
from app.models.user import User, UserRole  # noqa: F401
from app.models.otp import OtpCode, OtpChannel, OtpPurpose  # noqa: F401
from app.models.password_reset import PasswordResetToken  # noqa: F401
from app.models.social_account import SocialAccount, SocialProvider  # noqa: F401
from app.models.address import Address, AddressType  # noqa: F401
from app.models.preference import UserPreference  # noqa: F401
from app.models.audit_log import UserAuditLog, AuditAction  # noqa: F401

__all__ = [
    "User",
    "UserRole",
    "OtpCode",
    "OtpChannel",
    "OtpPurpose",
    "PasswordResetToken",
    "SocialAccount",
    "SocialProvider",
    "Address",
    "AddressType",
    "UserPreference",
    "AuditAction",
    "UserAuditLog",
]
