"""
API routes for Amazon Multi-Channel Fulfillment (MCF).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.amazon_mcf import (
    FulfillmentOrderCreate,
)
from app.services.amazon_mcf_service import (
    AmazonMCFService,
)

router = APIRouter(
    prefix="/amazon-mcf",
    tags=["Amazon MCF"],
)

service = AmazonMCFService()


# ==========================================================
# CREATE FULFILLMENT ORDER
# ==========================================================

@router.post(
    "/orders",
)
async def create_order(
    order: FulfillmentOrderCreate,
):
    try:
        return await service.create_order(order)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ==========================================================
# LIST ORDERS
# ==========================================================

@router.get(
    "/orders",
)
async def list_orders():
    try:
        return await service.list_orders()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ==========================================================
# GET ORDER
# ==========================================================

@router.get(
    "/orders/{order_id}",
)
async def get_order(
    order_id: str,
):
    try:
        return await service.get_order(
            order_id
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ==========================================================
# CANCEL ORDER
# ==========================================================

@router.delete(
    "/orders/{order_id}",
)
async def cancel_order(
    order_id: str,
):
    try:
        return await service.cancel_order(
            order_id
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ==========================================================
# TRACK SHIPMENT
# ==========================================================

@router.get(
    "/orders/{order_id}/tracking",
)
async def tracking(
    order_id: str,
):
    try:
        return await service.get_tracking(
            order_id
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ==========================================================
# INVENTORY
# ==========================================================

@router.get(
    "/inventory",
)
async def inventory():
    try:
        return await service.get_inventory()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )