from app.models.customer_address import CustomerAddress
from app.models.customer_audit import CustomerAudit
from app.models.customer_feedback import CustomerFeedback
from app.models.customer_interaction import CustomerInteraction
from app.models.customer_note import CustomerNote
from app.models.customer_preference import CustomerPreference
from app.models.customer_profile import CustomerProfile
from app.models.customer_segment import CustomerSegment
from app.models.customer_tag import CustomerTag
from app.models.customer_timeline import CustomerTimeline

from app.models.campaign import Campaign
from app.models.campaign_audience import CampaignAudience
from app.models.campaign_history import CampaignHistory

from app.models.loyalty_transaction import LoyaltyTransaction

from app.models.support_ticket import SupportTicket
from app.models.support_ticket_attachment import (
    SupportTicketAttachment,
)
from app.models.support_ticket_history import (
    SupportTicketHistory,
)
from app.models.support_ticket_note import SupportTicketNote

"""
CRM Models.
"""

from .affiliate import Affiliate
from .affiliate_click import AffiliateClick
from .affiliate_commission import AffiliateCommission
from .affiliate_coupon import AffiliateCoupon
from .affiliate_payout import AffiliatePayout
from .affiliate_referral import AffiliateReferral

__all__ = [
    "Affiliate",
    "AffiliateReferral",
    "AffiliateClick",
    "AffiliateCommission",
    "AffiliatePayout",
    "AffiliateCoupon",
    "CustomerAddress",
    "CustomerAudit",
    "CustomerFeedback",
    "CustomerInteraction",
    "CustomerNote",
    "CustomerPreference",
    "CustomerProfile",
    "CustomerSegment",
    "CustomerTag",
    "CustomerTimeline",
    "Campaign",
    "CampaignAudience",
    "CampaignHistory",
    "LoyaltyTransaction",
    "SupportTicket",
    "SupportTicketAttachment",
    "SupportTicketHistory",
    "SupportTicketNote",
]