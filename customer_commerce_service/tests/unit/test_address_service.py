"""Unit tests for AddressService."""
import uuid

import pytest
from fastapi import HTTPException

from app.schemas.address import AddressCreate, AddressUpdate
from app.services.address_service import AddressService

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _addr(**kwargs):
    defaults = dict(
        label="Home",
        full_name="Test User",
        phone="9876543210",
        line1="123 Main St",
        city="Mumbai",
        state="Maharashtra",
        pincode="400001",
    )
    defaults.update(kwargs)
    return AddressCreate(**defaults)


class TestAddressService:
    @pytest.mark.asyncio
    async def test_create_address(self, db_session):
        svc = AddressService(db_session)
        addr = await svc.create_address(USER_ID, _addr())
        assert addr.city == "Mumbai"
        assert addr.is_default is False

    @pytest.mark.asyncio
    async def test_default_address_unsets_others(self, db_session):
        svc = AddressService(db_session)
        a1 = await svc.create_address(USER_ID, _addr(is_default=True))
        a2 = await svc.create_address(USER_ID, _addr(label="Office", is_default=True))
        addresses = await svc.list_addresses(USER_ID)
        defaults = [a for a in addresses if a.is_default]
        assert len(defaults) == 1
        assert defaults[0].id == a2.id

    @pytest.mark.asyncio
    async def test_set_default(self, db_session):
        svc = AddressService(db_session)
        a1 = await svc.create_address(USER_ID, _addr())
        a2 = await svc.create_address(USER_ID, _addr(label="Office"))
        await svc.set_default(USER_ID, a1.id)
        addresses = await svc.list_addresses(USER_ID)
        # Default should be first
        assert addresses[0].id == a1.id
        assert addresses[0].is_default is True

    @pytest.mark.asyncio
    async def test_delete_address(self, db_session):
        svc = AddressService(db_session)
        addr = await svc.create_address(USER_ID, _addr())
        await svc.delete_address(USER_ID, addr.id)
        addresses = await svc.list_addresses(USER_ID)
        assert len(addresses) == 0

    @pytest.mark.asyncio
    async def test_delete_other_user_address_raises(self, db_session):
        svc = AddressService(db_session)
        addr = await svc.create_address(USER_ID, _addr())
        other_user = uuid.uuid4()
        with pytest.raises(HTTPException) as exc:
            await svc.delete_address(other_user, addr.id)
        assert exc.value.status_code == 404
