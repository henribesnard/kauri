"""
Pydantic schemas for subscription and quota management
"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


class SubscriptionTierSchema(BaseModel):
    """Schema for subscription tier information"""
    tier_id: str
    tier_name: str
    tier_name_fr: str
    tier_description: Optional[str] = None
    tier_description_fr: Optional[str] = None

    # Quotas (None = unlimited)
    messages_per_day: Optional[int] = None
    messages_per_month: Optional[int] = None
    tokens_per_month: Optional[int] = None

    # Pricing (FCFA)
    price_monthly: int
    price_annual: Optional[int] = None

    # Features
    has_document_sourcing: bool
    has_pdf_generation: bool
    has_priority_support: bool
    has_custom_training: bool
    has_api_access: bool

    # Display
    display_order: int
    is_active: bool
    is_visible: bool

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserQuotaInfo(BaseModel):
    """Schema for user quota status"""
    user_id: str
    subscription_tier: str
    subscription_status: str

    # Tier info
    tier_name: str
    tier_name_fr: str

    # Quota limits (None = unlimited)
    messages_per_day_limit: Optional[int] = None
    messages_per_month_limit: Optional[int] = None
    tokens_per_month_limit: Optional[int] = None

    # Current usage
    messages_today: int = 0
    messages_this_month: int = 0
    tokens_this_month: int = 0

    # Remaining quotas (None = unlimited)
    messages_remaining_today: Optional[int] = None
    messages_remaining_month: Optional[int] = None
    tokens_remaining_month: Optional[int] = None

    # Status flags
    can_send_message: bool
    is_quota_exceeded: bool
    needs_upgrade: bool
    warning_threshold_reached: bool = False  # True if at 80% or more

    # Dates
    usage_date: date
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUsageSchema(BaseModel):
    """Schema for user usage tracking"""
    id: str
    user_id: str
    usage_date: date

    messages_today: int
    messages_this_month: int
    tokens_this_month: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UsageLogSchema(BaseModel):
    """Schema for usage audit logs"""
    id: str
    user_id: str
    event_type: str
    event_timestamp: datetime

    messages_count: Optional[int] = None
    tokens_count: Optional[int] = None

    quota_tier: Optional[str] = None
    quota_status: Optional[str] = None
    request_ip: Optional[str] = None
    user_agent: Optional[str] = None

    event_metadata: Optional[dict] = None

    created_at: datetime

    class Config:
        from_attributes = True


class QuotaExceededResponse(BaseModel):
    """Response when quota is exceeded"""
    error: str = "quota_exceeded"
    message: str
    quota_info: UserQuotaInfo
    upgrade_url: str = "/pricing"
    reset_time: Optional[datetime] = None  # When quota will reset


class SubscriptionUpgradeRequest(BaseModel):
    """Request to upgrade subscription"""
    target_tier: str = Field(..., description="Target subscription tier (pro, max, enterprise)")
    payment_method: str = Field(..., description="Payment method (cinetpay, etc.)")
    annual_billing: bool = Field(default=False, description="Use annual billing")


class SubscriptionUpgradeResponse(BaseModel):
    """Response after upgrade request"""
    success: bool
    message: str
    payment_url: Optional[str] = None  # CinetPay payment URL
    transaction_id: Optional[str] = None
    new_tier: Optional[str] = None
    effective_date: Optional[datetime] = None
