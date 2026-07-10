"""
Business logic for building sitemap XML documents from `SitemapEntry`
rows, and for splitting large entity sets into multiple sitemap files
plus a sitemap index, per the 50,000-URL / 50MB sitemap protocol limit.
"""
from __future__ import annotations

from datetime import datetime, timezone
from xml.sax.saxutils import escape

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.sitemap import SitemapEntityType, SitemapEntry, SitemapFile

settings = get_settings()

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _url_xml(entry: SitemapEntry) -> str:
    return (
        "<url>"
        f"<loc>{escape(entry.loc)}</loc>"
        f"<lastmod>{entry.lastmod.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}</lastmod>"
        f"<changefreq>{entry.changefreq.value}</changefreq>"
        f"<priority>{entry.priority:.1f}</priority>"
        "</url>"
    )


def render_urlset(entries: list[SitemapEntry]) -> str:
    body = "".join(_url_xml(e) for e in entries)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="{SITEMAP_NS}">{body}</urlset>'
    )


def render_sitemap_index(file_names: list[str]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = "".join(
        f"<sitemap><loc>{settings.PUBLIC_BASE_URL}/sitemaps/{name}</loc>"
        f"<lastmod>{now}</lastmod></sitemap>"
        for name in file_names
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<sitemapindex xmlns="{SITEMAP_NS}">{entries}</sitemapindex>'
    )


class SitemapService:
    """Reads/writes sitemap entries and generates cached XML files."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert_entry(
        self,
        *,
        entity_type: SitemapEntityType,
        entity_id: str,
        loc: str,
        lastmod: datetime,
        changefreq,
        priority: float,
        is_active: bool = True,
    ) -> SitemapEntry:
        result = await self.db.execute(
            select(SitemapEntry).where(
                SitemapEntry.entity_type == entity_type,
                SitemapEntry.entity_id == entity_id,
            )
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            entry = SitemapEntry(
                entity_type=entity_type,
                entity_id=entity_id,
                loc=loc,
                lastmod=lastmod,
                changefreq=changefreq,
                priority=priority,
                is_active=is_active,
            )
            self.db.add(entry)
        else:
            entry.loc = loc
            entry.lastmod = lastmod
            entry.changefreq = changefreq
            entry.priority = priority
            entry.is_active = is_active
        await self.db.flush()
        return entry

    async def deactivate_entry(self, entity_type: SitemapEntityType, entity_id: str) -> None:
        result = await self.db.execute(
            select(SitemapEntry).where(
                SitemapEntry.entity_type == entity_type,
                SitemapEntry.entity_id == entity_id,
            )
        )
        entry = result.scalar_one_or_none()
        if entry:
            entry.is_active = False
            await self.db.flush()

    async def generate_files_for_type(self, entity_type: SitemapEntityType) -> list[SitemapFile]:
        """Paginate active entries of one type into <=N-url sitemap files."""
        result = await self.db.execute(
            select(SitemapEntry)
            .where(SitemapEntry.entity_type == entity_type, SitemapEntry.is_active.is_(True))
            .order_by(SitemapEntry.updated_at.desc())
        )
        entries = list(result.scalars().all())
        chunk_size = settings.SITEMAP_MAX_URLS_PER_FILE
        chunks = [entries[i : i + chunk_size] for i in range(0, len(entries), chunk_size)] or [[]]

        generated: list[SitemapFile] = []
        for idx, chunk in enumerate(chunks, start=1):
            name = f"sitemap-{entity_type.value}-{idx}.xml"
            xml_content = render_urlset(chunk)
            file_result = await self.db.execute(
                select(SitemapFile).where(SitemapFile.name == name)
            )
            sitemap_file = file_result.scalar_one_or_none()
            if sitemap_file is None:
                sitemap_file = SitemapFile(
                    name=name,
                    entity_type=entity_type,
                    part_number=idx,
                    url_count=len(chunk),
                    xml_content=xml_content,
                )
                self.db.add(sitemap_file)
            else:
                sitemap_file.url_count = len(chunk)
                sitemap_file.xml_content = xml_content
            generated.append(sitemap_file)
        await self.db.flush()
        return generated

    async def regenerate_index(self) -> SitemapFile:
        result = await self.db.execute(
            select(SitemapFile).where(SitemapFile.name != "sitemap-index.xml")
        )
        names = [f.name for f in result.scalars().all()]
        xml_content = render_sitemap_index(sorted(names))
        idx_result = await self.db.execute(
            select(SitemapFile).where(SitemapFile.name == "sitemap-index.xml")
        )
        index_file = idx_result.scalar_one_or_none()
        if index_file is None:
            index_file = SitemapFile(
                name="sitemap-index.xml", entity_type=None, url_count=len(names),
                xml_content=xml_content,
            )
            self.db.add(index_file)
        else:
            index_file.xml_content = xml_content
            index_file.url_count = len(names)
        await self.db.flush()
        return index_file

    async def get_file(self, name: str) -> SitemapFile | None:
        result = await self.db.execute(select(SitemapFile).where(SitemapFile.name == name))
        return result.scalar_one_or_none()
