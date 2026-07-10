"""Business logic for redirect rule and canonical URL management."""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.redirects import CanonicalUrl, RedirectRule


class RedirectService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_rule(
        self, *, source_path: str, target_path: str, redirect_type: int,
        reason: str | None, is_active: bool = True, synced_from_catalog: bool = False,
    ) -> RedirectRule:
        rule = RedirectRule(
            source_path=source_path,
            target_path=target_path,
            redirect_type=redirect_type,
            reason=reason,
            is_active=is_active,
            synced_from_catalog=synced_from_catalog,
        )
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def get_rule(self, rule_id: str) -> RedirectRule | None:
        return await self.db.get(RedirectRule, rule_id)

    async def lookup_by_source(self, source_path: str) -> RedirectRule | None:
        result = await self.db.execute(
            select(RedirectRule).where(
                RedirectRule.source_path == source_path, RedirectRule.is_active.is_(True)
            )
        )
        rule = result.scalar_one_or_none()
        if rule:
            await self.db.execute(
                update(RedirectRule)
                .where(RedirectRule.id == rule.id)
                .values(hit_count=RedirectRule.hit_count + 1)
            )
        return rule

    async def list_rules(self, limit: int = 100, offset: int = 0) -> list[RedirectRule]:
        result = await self.db.execute(
            select(RedirectRule).order_by(RedirectRule.updated_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def sync_from_catalog(self, catalog_redirects: list[dict]) -> int:
        """Idempotently upsert redirect rules owned upstream by Catalog."""
        synced = 0
        for item in catalog_redirects:
            result = await self.db.execute(
                select(RedirectRule).where(RedirectRule.source_path == item["source_path"])
            )
            rule = result.scalar_one_or_none()
            if rule is None:
                rule = RedirectRule(
                    source_path=item["source_path"],
                    target_path=item["target_path"],
                    redirect_type=item.get("redirect_type", 301),
                    reason=item.get("reason", "catalog_sync"),
                    synced_from_catalog=True,
                )
                self.db.add(rule)
            else:
                rule.target_path = item["target_path"]
                rule.redirect_type = item.get("redirect_type", 301)
                rule.synced_from_catalog = True
            synced += 1
        await self.db.flush()
        return synced

    async def upsert_canonical(
        self, *, entity_type: str, entity_id: str, canonical_path: str, notes: str | None = None
    ) -> CanonicalUrl:
        result = await self.db.execute(
            select(CanonicalUrl).where(
                CanonicalUrl.entity_type == entity_type, CanonicalUrl.entity_id == entity_id
            )
        )
        canonical = result.scalar_one_or_none()
        if canonical is None:
            canonical = CanonicalUrl(
                entity_type=entity_type,
                entity_id=entity_id,
                canonical_path=canonical_path,
                notes=notes,
            )
            self.db.add(canonical)
        else:
            canonical.canonical_path = canonical_path
            canonical.notes = notes
        await self.db.flush()
        return canonical

    async def get_canonical(self, entity_type: str, entity_id: str) -> CanonicalUrl | None:
        result = await self.db.execute(
            select(CanonicalUrl).where(
                CanonicalUrl.entity_type == entity_type, CanonicalUrl.entity_id == entity_id
            )
        )
        return result.scalar_one_or_none()
