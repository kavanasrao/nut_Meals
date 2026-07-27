"""JWT decoding and RBAC FastAPI dependencies."""
from typing import Annotated, List
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer()


class TokenPayload:
    def __init__(self, user_id: UUID, roles: List[str], email: str):
        self.user_id = user_id
        self.roles = roles
        self.email = email


def _decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return TokenPayload(
            user_id=UUID(payload["sub"]),
            roles=payload.get("roles", ["customer"]),
            email=payload.get("email", ""),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(bearer_scheme)],
) -> TokenPayload:
    return _decode_token(credentials.credentials)


def require_roles(*roles: str):
    async def _check(
        current_user: Annotated[TokenPayload, Depends(get_current_user)],
    ) -> TokenPayload:
        if not any(r in current_user.roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {list(roles)}",
            )
        return current_user
    return _check


require_customer = require_roles("customer", "admin")
require_admin = require_roles("admin")
