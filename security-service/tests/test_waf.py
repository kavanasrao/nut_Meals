"""Unit tests for the WAF rule engine + integration tests for the /waf API."""
import uuid

import fakeredis.aioredis
import pytest

from app.services import waf_engine as waf_engine_module
from app.services.waf_engine import EvaluationInput, WafEngine
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Replace the module-level Redis client with an in-memory fake for all WAF tests."""
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(waf_engine_module, "_redis", fake)
    yield fake


class TestWafEngineMatching:
    """Pure logic tests: no HTTP layer, exercises the regex/CIDR/rate-limit rules directly."""

    def _rule(self, **overrides):
        base = {
            "id": str(uuid.uuid4()),
            "name": "test-rule",
            "rule_type": "sql_injection",
            "pattern": r"(\bunion\b.+\bselect\b)|(\bor\b\s+1=1)",
            "action": "block",
            "severity": 8,
            "applies_to_service": None,
        }
        base.update(overrides)
        return base

    def test_sqli_pattern_matches_malicious_query(self, db_session):
        engine = WafEngine(db_session)
        rule = self._rule()
        evaluation = EvaluationInput(
            method="GET",
            path="/products",
            query_string="id=1 OR 1=1",
            headers={},
            body_snippet="",
            source_ip="10.0.0.1",
            service="orders",
        )
        fragment = engine._match(rule, evaluation)
        assert fragment is not None

    def test_sqli_pattern_does_not_match_benign_query(self, db_session):
        engine = WafEngine(db_session)
        rule = self._rule()
        evaluation = EvaluationInput(
            method="GET",
            path="/products",
            query_string="category=snacks",
            headers={},
            body_snippet="",
            source_ip="10.0.0.1",
            service="orders",
        )
        fragment = engine._match(rule, evaluation)
        assert fragment is None

    def test_ip_blocklist_matches_cidr(self, db_session):
        engine = WafEngine(db_session)
        rule = self._rule(rule_type="ip_blocklist", pattern="192.168.1.0/24")
        evaluation = EvaluationInput(
            method="GET", path="/", query_string="", headers={}, body_snippet="",
            source_ip="192.168.1.55", service="orders",
        )
        fragment = engine._match(rule, evaluation)
        assert fragment == "192.168.1.55"

    def test_ip_blocklist_does_not_match_outside_range(self, db_session):
        engine = WafEngine(db_session)
        rule = self._rule(rule_type="ip_blocklist", pattern="192.168.1.0/24")
        evaluation = EvaluationInput(
            method="GET", path="/", query_string="", headers={}, body_snippet="",
            source_ip="10.0.0.5", service="orders",
        )
        assert engine._match(rule, evaluation) is None

    def test_csrf_rule_flags_missing_header_on_mutating_request(self, db_session):
        engine = WafEngine(db_session)
        rule = self._rule(rule_type="csrf", pattern="X-CSRF-Token")
        evaluation = EvaluationInput(
            method="POST", path="/orders", query_string="", headers={}, body_snippet="",
            source_ip="10.0.0.1", service="orders",
        )
        assert engine._match(rule, evaluation) is not None

    def test_csrf_rule_passes_when_header_present(self, db_session):
        engine = WafEngine(db_session)
        rule = self._rule(rule_type="csrf", pattern="X-CSRF-Token")
        evaluation = EvaluationInput(
            method="POST", path="/orders", query_string="", headers={"X-CSRF-Token": "abc"},
            body_snippet="", source_ip="10.0.0.1", service="orders",
        )
        assert engine._match(rule, evaluation) is None

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_after_threshold(self, db_session):
        engine = WafEngine(db_session)
        rule = self._rule(rule_type="rate_limit", pattern='{"window_s": 60, "max_requests": 2}')
        evaluation = EvaluationInput(
            method="GET", path="/", query_string="", headers={}, body_snippet="",
            source_ip="10.0.0.9", service="orders",
        )
        r1 = await engine.check_rate_limit(rule, evaluation)
        r2 = await engine.check_rate_limit(rule, evaluation)
        r3 = await engine.check_rate_limit(rule, evaluation)
        assert r1 is None
        assert r2 is None
        assert r3 is not None  # third request within the window exceeds max_requests=2


@pytest.mark.asyncio
class TestWafApi:
    async def test_create_rule_requires_permission(self, client, db_session):
        resp = await client.post(
            "/waf/rules",
            json={
                "name": "block-sqli",
                "rule_type": "sql_injection",
                "pattern": r"union.+select",
                "action": "block",
                "severity": 9,
            },
            headers=auth_headers(user_id="no-permissions-user"),
        )
        assert resp.status_code == 403

    async def test_create_and_list_rule(self, client, db_session, admin_user):
        create_resp = await client.post(
            "/waf/rules",
            json={
                "name": "block-sqli-2",
                "rule_type": "sql_injection",
                "pattern": r"union.+select",
                "action": "block",
                "severity": 9,
            },
            headers=auth_headers(user_id=admin_user),
        )
        assert create_resp.status_code == 201
        rule_id = create_resp.json()["id"]

        list_resp = await client.get("/waf/rules", headers=auth_headers(user_id=admin_user))
        assert list_resp.status_code == 200
        assert any(r["id"] == rule_id for r in list_resp.json())

    async def test_evaluate_endpoint_allows_benign_request(self, client, db_session, admin_user):
        resp = await client.post(
            "/waf/evaluate",
            json={
                "method": "GET",
                "path": "/products",
                "query_string": "category=snacks",
                "headers": {},
                "body_snippet": "",
                "source_ip": "10.0.0.1",
                "service": "orders",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["allowed"] is True
