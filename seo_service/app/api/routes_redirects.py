"""
Redirect and canonical URL management endpoints.

Read (lookup) endpoints are unauthenticated internal calls used by the
edge/gateway to resolve 301/302s on the fly; write endpoints are
RBAC-protected and audit-logged.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import DbSession
from app.core.audit import record_audit_event
from app.core.security import CurrentUser, Role, require_roles
from app.schemas.redirects import (
    CanonicalUrlIn,
    CanonicalUrlOut,
    RedirectLookupOut,
    RedirectRuleIn,
    RedirectRuleOut,
)
from app.services.redirect_service import RedirectService

router = APIRouter(prefix="/redirects", tags=["redirects"])


@router.get("/lookup", response_model=RedirectLookupOut)
async def lookup_redirect(source_path: str, db: DbSession) -> RedirectLookupOut:
    service = RedirectService(db)
    rule = await service.lookup_by_source(source_path)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No redirect found")
    return RedirectLookupOut(
        source_path=rule.source_path,
        target_path=rule.target_path,
        redirect_type=int(rule.redirect_type),
    )


@router.get("", response_model=list[RedirectRuleOut])
async def list_redirects(
    db: DbSession,
    user: Annotated[CurrentUser, Depends(require_roles(Role.SEO_EDITOR, Role.ADMIN, Role.VIEWER))],
    limit: int = 100,
    offset: int = 0,
) -> list[RedirectRuleOut]:
    service = RedirectService(db)
    rules = await service.list_rules(limit=limit, offset=offset)
    return [RedirectRuleOut.model_validate(r) for r in rules]


@router.post("", response_model=RedirectRuleOut, status_code=status.HTTP_201_CREATED)
async def create_redirect(
    payload: RedirectRuleIn,
    request: Request,
    db: DbSession,
    user: Annotated[CurrentUser, Depends(require_roles(Role.SEO_EDITOR, Role.ADMIN))],
) -> RedirectRuleOut:
    service = RedirectService(db)
    rule = await service.create_rule(
        source_path=payload.source_path,
        target_path=payload.target_path,
        redirect_type=payload.redirect_type.value,
        reason=payload.reason,
        is_active=payload.is_active,
    )
    await record_audit_event(
        db,
        user=user,
        action="redirect.create",
        target_type="redirect_rule",
        target_id=str(rule.id),
        after_state=payload.model_dump(mode="json"),
        ip_address=request.client.host if request.client else None,
    )
    return RedirectRuleOut.model_validate(rule)


@router.put("/canonical", response_model=CanonicalUrlOut)
async def upsert_canonical(
    payload: CanonicalUrlIn,
    request: Request,
    db: DbSession,
    user: Annotated[CurrentUser, Depends(require_roles(Role.SEO_EDITOR, Role.ADMIN))],
) -> CanonicalUrlOut:
    service = RedirectService(db)
    before = await service.get_canonical(payload.entity_type, payload.entity_id)
    before_state = (
        {"canonical_path": before.canonical_path} if before else None
    )
    canonical = await service.upsert_canonical(
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        canonical_path=payload.canonical_path,
        notes=payload.notes,
    )
    await record_audit_event(
        db,
        user=user,
        action="canonical.upsert",
        target_type="canonical_url",
        target_id=str(canonical.id),
        before_state=before_state,
        after_state={"canonical_path": canonical.canonical_path},
        ip_address=request.client.host if request.client else None,
    )
    return CanonicalUrlOut.model_validate(canonical)


@router.get("/canonical", response_model=CanonicalUrlOut)
async def get_canonical(entity_type: str, entity_id: str, db: DbSession) -> CanonicalUrlOut:
    service = RedirectService(db)
    canonical = await service.get_canonical(entity_type, entity_id)
    if canonical is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No canonical URL set")
    return CanonicalUrlOut.model_validate(canonical)
