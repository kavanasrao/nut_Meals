"""Seed script — creates the first superadmin account.

Run once after `docker compose up`:
    docker compose exec admin-service python scripts/seed_superadmin.py

Or locally:
    python scripts/seed_superadmin.py
"""
from __future__ import annotations

import asyncio
import os
import sys

# Allow running from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal, Base, engine
from app.core.security import hash_password
from app.models.models import AdminRole, AdminUser


async def seed() -> None:
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    email = os.getenv("SUPERADMIN_EMAIL", "superadmin@nutmeals.in")
    password = os.getenv("SUPERADMIN_PASSWORD", "ChangeMe@123!")
    full_name = os.getenv("SUPERADMIN_NAME", "Super Admin")

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(AdminUser).where(AdminUser.email == email))
        if existing.scalar_one_or_none():
            print(f"Superadmin '{email}' already exists — skipping.")
            return

        import uuid
        admin = AdminUser(
            id=uuid.uuid4(),
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=AdminRole.SUPERADMIN,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        print(f"✅ Superadmin created: {email}")
        print("⚠️  Change the default password immediately in production!")


if __name__ == "__main__":
    asyncio.run(seed())
