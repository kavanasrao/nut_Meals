"""Shared FastAPI dependencies for the API layer."""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.catalog_client import CatalogClient, get_catalog_client

DbSession = Annotated[AsyncSession, Depends(get_db)]
Catalog = Annotated[CatalogClient, Depends(get_catalog_client)]
