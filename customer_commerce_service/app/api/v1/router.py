"""Central API v1 router."""
from fastapi import APIRouter

from app.api.v1.endpoints import cart, wishlist, coupons, addresses, invoices

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(cart.router)
api_router.include_router(wishlist.router)
api_router.include_router(coupons.router)
api_router.include_router(addresses.router)
api_router.include_router(invoices.router)
