"""
WAF management & evaluation API.

- `/waf/rules*` — CRUD for policies, restricted to users holding `waf:manage_rules`.
- `/waf/incidents` — read-only incident feed, restricted to `waf:read`.
- `/waf/evaluate` — lets other services ask "would you block this request?"
  out-of-band (used by services that can't run the middleware directly, e.g.
  batch/webhook consumers).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUserDep, DbDep, require_permission
from app.models.waf import WafRule
from app.schemas.waf import (
    WafEvaluateRequest,
    WafEvaluateResponse,
    WafIncidentOut,
    WafRuleCreate,
    WafRuleOut,
    WafRuleUpdate,
)
from app.services.waf_engine import EvaluationInput, WafEngine

router = APIRouter(prefix="/waf", tags=["waf"])


@router.post(
    "/rules",
    response_model=WafRuleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("waf:manage_rules"))],
)
async def create_rule(payload: WafRuleCreate, db: DbDep, user: CurrentUserDep):
    """Create a new WAF rule. Requires `waf:manage_rules`."""
    rule = WafRule(**payload.model_dump(), created_by=user.user_id)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    await WafEngine.invalidate_cache()
    return rule


@router.get("/rules", response_model=list[WafRuleOut], dependencies=[Depends(require_permission("waf:read"))])
async def list_rules(db: DbDep, is_active: bool | None = Query(default=None)):
    """List configured WAF rules, optionally filtered by active status."""
    from sqlalchemy import select

    stmt = select(WafRule)
    if is_active is not None:
        stmt = stmt.where(WafRule.is_active == is_active)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch(
    "/rules/{rule_id}",
    response_model=WafRuleOut,
    dependencies=[Depends(require_permission("waf:manage_rules"))],
)
async def update_rule(rule_id: uuid.UUID, payload: WafRuleUpdate, db: DbDep):
    """Partially update a rule (e.g. disable it, tune severity). Requires `waf:manage_rules`."""
    rule = await db.get(WafRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    await WafEngine.invalidate_cache()
    return rule


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("waf:manage_rules"))],
)
async def delete_rule(rule_id: uuid.UUID, db: DbDep):
    """Delete a WAF rule. Requires `waf:manage_rules`."""
    rule = await db.get(WafRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    await db.commit()
    await WafEngine.invalidate_cache()


@router.get(
    "/incidents",
    response_model=list[WafIncidentOut],
    dependencies=[Depends(require_permission("waf:read"))],
)
async def list_incidents(db: DbDep, service: str | None = None, limit: int = Query(100, le=1000)):
    """Read-only feed of requests that matched a WAF rule. Requires `waf:read`."""
    from sqlalchemy import select

    from app.models.waf import WafIncident

    stmt = select(WafIncident).order_by(WafIncident.created_at.desc()).limit(limit)
    if service:
        stmt = stmt.where(WafIncident.service == service)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/evaluate", response_model=WafEvaluateResponse)
async def evaluate_request(payload: WafEvaluateRequest, db: DbDep):
    """Out-of-band evaluation endpoint for services that can't embed the WAF middleware directly.

    No permission check: any authenticated internal service can ask "should I
    allow this?" — this endpoint only reads rules/records incidents, it never
    mutates policy.
    """
    engine = WafEngine(db)
    evaluation = EvaluationInput(
        method=payload.method,
        path=payload.path,
        query_string=payload.query_string or "",
        headers=payload.headers,
        body_snippet=payload.body_snippet or "",
        source_ip=payload.source_ip,
        service=payload.service,
    )
    allowed, matched_rule, fragment = await engine.evaluate(evaluation)

    incident_out = None
    rule_out = None
    if matched_rule is not None:
        incident = await engine.record_incident(evaluation, matched_rule, fragment or "", payload.user_id)
        incident_out = WafIncidentOut.model_validate(incident)
        # matched_rule is a dict (cached form), not the ORM row, so build a minimal WafRuleOut-like view
        rule_out = None  # full rule details available via GET /waf/rules/{id} if needed

    return WafEvaluateResponse(allowed=allowed, matched_rule=rule_out, incident=incident_out)
