"""
WAF rule evaluation engine.

Rules are loaded from Postgres and cached in Redis (short TTL) so the
per-request evaluation path in the middleware doesn't hit the DB on every
call. This module contains the pure evaluation logic; app/middleware/waf_middleware.py
wires it into the ASGI request pipeline.
"""
import ipaddress
import json
import re
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.waf import WafAction, WafIncident, WafRule, WafRuleType

settings = get_settings()

_redis: Optional[aioredis.Redis] = None
_RULES_CACHE_KEY = "waf:rules:active"
_RULES_CACHE_TTL_S = 15


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


class EvaluationInput:
    """Normalized view of an inbound request, whatever service it targets."""

    def __init__(
        self,
        method: str,
        path: str,
        query_string: str,
        headers: dict[str, str],
        body_snippet: str,
        source_ip: str,
        service: str,
    ):
        self.method = method
        self.path = path
        self.query_string = query_string or ""
        self.headers = headers or {}
        self.body_snippet = (body_snippet or "")[: settings.WAF_MAX_BODY_BYTES]
        self.source_ip = source_ip
        self.service = service

    @property
    def searchable_text(self) -> str:
        header_blob = " ".join(f"{k}:{v}" for k, v in self.headers.items())
        return " ".join([self.path, self.query_string, header_blob, self.body_snippet])


class WafEngine:
    """Evaluates a request against the active, cached rule set."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _load_active_rules(self) -> list[dict]:
        r = _get_redis()
        cached = await r.get(_RULES_CACHE_KEY)
        if cached:
            return json.loads(cached)

        stmt = select(WafRule).where(WafRule.is_active.is_(True))
        result = await self.db.execute(stmt)
        rules = result.scalars().all()
        serialized = [
            {
                "id": str(rule.id),
                "name": rule.name,
                "rule_type": rule.rule_type.value,
                "pattern": rule.pattern,
                "action": rule.action.value,
                "severity": rule.severity,
                "applies_to_service": rule.applies_to_service,
            }
            for rule in rules
        ]
        await r.set(_RULES_CACHE_KEY, json.dumps(serialized), ex=_RULES_CACHE_TTL_S)
        return serialized

    @staticmethod
    async def invalidate_cache() -> None:
        """Call after any create/update/delete of a WafRule."""
        r = _get_redis()
        await r.delete(_RULES_CACHE_KEY)

    def _rule_applies(self, rule: dict, evaluation: EvaluationInput) -> bool:
        if rule["applies_to_service"] and rule["applies_to_service"] != evaluation.service:
            return False
        return True

    def _match(self, rule: dict, evaluation: EvaluationInput) -> Optional[str]:
        """Return the matched fragment (truncated) if the rule fires, else None."""
        rule_type = rule["rule_type"]

        if rule_type == WafRuleType.IP_BLOCKLIST.value:
            try:
                network = ipaddress.ip_network(rule["pattern"], strict=False)
                if ipaddress.ip_address(evaluation.source_ip) in network:
                    return evaluation.source_ip
            except ValueError:
                return None
            return None

        if rule_type in (WafRuleType.SQLI.value, WafRuleType.XSS.value, WafRuleType.CUSTOM_REGEX.value):
            try:
                compiled = re.compile(rule["pattern"], re.IGNORECASE)
            except re.error:
                return None
            match = compiled.search(evaluation.searchable_text)
            if match:
                return match.group(0)[:256]
            return None

        if rule_type == WafRuleType.CSRF.value:
            # Pattern is a required-header-name (e.g. "X-CSRF-Token").
            required_header = rule["pattern"].strip()
            if evaluation.method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
                if required_header and required_header not in evaluation.headers:
                    return f"missing header {required_header}"
            return None

        # RATE_LIMIT is handled separately (stateful, needs a sliding window) --
        # see check_rate_limit() below rather than the stateless _match path.
        return None

    async def check_rate_limit(self, rule: dict, evaluation: EvaluationInput) -> Optional[str]:
        try:
            config = json.loads(rule["pattern"])
            window_s = int(config["window_s"])
            max_requests = int(config["max_requests"])
        except (ValueError, KeyError, TypeError):
            return None

        r = _get_redis()
        key = f"waf:rl:{rule['id']}:{evaluation.source_ip}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window_s)
        if count > max_requests:
            return f"{count} requests in {window_s}s (limit {max_requests})"
        return None

    async def evaluate(self, evaluation: EvaluationInput) -> tuple[bool, Optional[dict], Optional[str]]:
        """Returns (allowed, matched_rule_dict_or_None, matched_fragment_or_None)."""
        rules = await self._load_active_rules()
        for rule in rules:
            if not self._rule_applies(rule, evaluation):
                continue

            if rule["rule_type"] == WafRuleType.RATE_LIMIT.value:
                fragment = await self.check_rate_limit(rule, evaluation)
            else:
                fragment = self._match(rule, evaluation)

            if fragment is not None:
                blocked = rule["action"] == WafAction.BLOCK.value and settings.WAF_BLOCK_MODE
                return (not blocked, rule, fragment)

        return (True, None, None)

    async def record_incident(
        self,
        evaluation: EvaluationInput,
        rule: dict,
        fragment: str,
        user_id: Optional[str] = None,
    ) -> WafIncident:
        incident = WafIncident(
            rule_id=rule["id"],
            rule_name=rule["name"],
            rule_type=WafRuleType(rule["rule_type"]),
            action_taken=WafAction(rule["action"]),
            source_ip=evaluation.source_ip,
            method=evaluation.method,
            path=evaluation.path,
            service=evaluation.service,
            matched_fragment=fragment,
            user_id=user_id,
        )
        self.db.add(incident)
        await self.db.commit()
        await self.db.refresh(incident)
        return incident
