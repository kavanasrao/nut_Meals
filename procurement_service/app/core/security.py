"""
JWT auth. Tokens are issued by the central Auth service; this service only
verifies them (shared JWT_SECRET_KEY, pulled from OCI Vault at deploy time).
"""
import uuid
from dataclasses import dataclass, field

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: uuid.UUID
    email: str
    roles: list[str] = field(default_factory=list)

    def has_role(self, *roles: str) -> bool:
        return any(r in self.roles for r in roles)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        ) from exc

    return CurrentUser(
        id=user_id,
        email=payload.get("email", ""),
        roles=payload.get("roles", []),
    )
