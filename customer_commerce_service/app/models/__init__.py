"""Import all models so Alembic autogenerate detects them."""
from app.models.base import Base  # noqa: F401
from app.models.cart import Cart, CartItem  # noqa: F401
from app.models.wishlist import WishlistItem  # noqa: F401
from app.models.coupon import Coupon, CouponUsage  # noqa: F401
from app.models.address import SavedAddress  # noqa: F401
from app.models.invoice import Invoice  # noqa: F401
