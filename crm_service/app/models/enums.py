from enum import Enum


class CustomerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"


class CustomerSource(str, Enum):
    WEBSITE = "WEBSITE"
    MOBILE_APP = "MOBILE_APP"
    ADMIN = "ADMIN"
    REFERRAL = "REFERRAL"
    MARKETPLACE = "MARKETPLACE"
    IMPORT = "IMPORT"


class AcquisitionChannel(str, Enum):
    ORGANIC = "ORGANIC"
    PAID = "PAID"
    SOCIAL = "SOCIAL"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    REFERRAL = "REFERRAL"
    DIRECT = "DIRECT"


class LoyaltyTier(str, Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"


class TimelineEvent(str, Enum):
    REGISTRATION = "REGISTRATION"
    LOGIN = "LOGIN"
    ORDER_CREATED = "ORDER_CREATED"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    SHIPMENT_CREATED = "SHIPMENT_CREATED"
    DELIVERED = "DELIVERED"
    RETURN_REQUESTED = "RETURN_REQUESTED"
    REFUND_COMPLETED = "REFUND_COMPLETED"
    SUPPORT_TICKET = "SUPPORT_TICKET"
    CAMPAIGN_INTERACTION = "CAMPAIGN_INTERACTION"


class InteractionType(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    PHONE = "PHONE"
    NOTE = "NOTE"


class TicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_CUSTOMER = "WAITING_CUSTOMER"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class CampaignType(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    PUSH = "PUSH"


class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class LoyaltyTransactionType(str, Enum):
    EARN = "EARN"
    REDEEM = "REDEEM"
    EXPIRE = "EXPIRE"
    ADJUSTMENT = "ADJUSTMENT"


class FeedbackRating(int, Enum):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    