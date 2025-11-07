"""
Routes pour la gestion des abonnements et quotas
/api/v1/subscription/*
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import structlog

from ...models.user import User
from ...schemas.subscription import (
    UserQuotaInfo,
    SubscriptionTierSchema,
    QuotaExceededResponse,
    SubscriptionUpgradeRequest,
    SubscriptionUpgradeResponse
)
from ...services.subscription_service import SubscriptionService
from ...utils.database import get_db
from ..routes.auth import get_current_user

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/subscription", tags=["subscription"])


@router.get("/quota", response_model=UserQuotaInfo)
async def get_my_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's quota status
    Used by the dashboard to display remaining messages
    """
    try:
        quota_info = SubscriptionService.get_user_quota_info(db, current_user.user_id)
        return quota_info
    except Exception as e:
        logger.error("get_quota_failed", user_id=current_user.user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quota information"
        )


@router.get("/tiers", response_model=list[SubscriptionTierSchema])
async def get_subscription_tiers(
    db: Session = Depends(get_db)
):
    """
    Get all available subscription tiers for the pricing page
    Public endpoint (no authentication required)
    """
    try:
        tiers = SubscriptionService.get_all_tiers(db, visible_only=True)
        return tiers
    except Exception as e:
        logger.error("get_tiers_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription tiers"
        )


@router.get("/tier/{tier_id}", response_model=SubscriptionTierSchema)
async def get_tier_details(
    tier_id: str,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific subscription tier
    Public endpoint
    """
    tier = SubscriptionService.get_tier_config(db, tier_id)
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tier {tier_id} not found"
        )
    return tier


@router.post("/upgrade", response_model=SubscriptionUpgradeResponse)
async def upgrade_subscription(
    request: SubscriptionUpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate subscription upgrade
    This will create a payment link with CinetPay in the future
    For now, just updates the subscription directly (testing)
    """
    try:
        # Verify target tier exists
        tier = SubscriptionService.get_tier_config(db, request.target_tier)
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier: {request.target_tier}"
            )

        # Check if user is already on this tier
        if current_user.subscription_tier == request.target_tier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already subscribed to this tier"
            )

        # TODO: In production, integrate with CinetPay here
        # For now, directly upgrade the subscription (testing only)
        success, message, updated_user = SubscriptionService.upgrade_subscription(
            db,
            current_user.user_id,
            request.target_tier,
            request.annual_billing
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        logger.info("subscription_upgraded",
                    user_id=current_user.user_id,
                    from_tier=current_user.subscription_tier,
                    to_tier=request.target_tier)

        return SubscriptionUpgradeResponse(
            success=True,
            message=message,
            new_tier=request.target_tier,
            effective_date=updated_user.subscription_start_date,
            # In production, would include:
            # payment_url="https://cinetpay.com/payment/...",
            # transaction_id="TX123456789"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("upgrade_failed",
                     user_id=current_user.user_id,
                     target_tier=request.target_tier,
                     error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process upgrade request"
        )


@router.get("/usage/stats")
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed usage statistics for the current user
    Includes historical data
    """
    try:
        # Get current quota info
        quota_info = SubscriptionService.get_user_quota_info(db, current_user.user_id)

        # Calculate percentage usage
        daily_usage_pct = None
        monthly_usage_pct = None

        if quota_info.messages_per_day_limit:
            daily_usage_pct = (quota_info.messages_today / quota_info.messages_per_day_limit) * 100

        if quota_info.messages_per_month_limit:
            monthly_usage_pct = (quota_info.messages_this_month / quota_info.messages_per_month_limit) * 100

        return {
            "quota_info": quota_info,
            "usage_percentages": {
                "daily": round(daily_usage_pct, 2) if daily_usage_pct else None,
                "monthly": round(monthly_usage_pct, 2) if monthly_usage_pct else None
            },
            "warnings": {
                "approaching_daily_limit": daily_usage_pct >= 80 if daily_usage_pct else False,
                "approaching_monthly_limit": monthly_usage_pct >= 80 if monthly_usage_pct else False
            }
        }

    except Exception as e:
        logger.error("get_usage_stats_failed",
                     user_id=current_user.user_id,
                     error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics"
        )
