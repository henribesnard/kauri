"""
Service pour la gestion des abonnements et quotas
"""
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.user import User, SubscriptionTier, UserUsage, UsageLog
from src.schemas.subscription import UserQuotaInfo


# Default tiers to seed when the reference table is empty/out-of-sync
DEFAULT_TIERS = [
    {
        "tier_id": "free",
        "tier_name": "Free",
        "tier_name_fr": "Gratuit",
        "tier_description": "Basic plan for students and casual users",
        "tier_description_fr": "Plan de base pour étudiants et usage occasionnel",
        "messages_per_day": 5,
        "messages_per_month": 150,
        "tokens_per_month": 100_000,
        "price_monthly": 0,
        "price_annual": None,
        "has_document_sourcing": False,
        "has_pdf_generation": False,
        "has_priority_support": False,
        "has_custom_training": False,
        "has_api_access": False,
        "display_order": 1,
        "is_active": True,
        "is_visible": True,
    },
    {
        "tier_id": "pro",
        "tier_name": "Pro",
        "tier_name_fr": "Pro",
        "tier_description": "Professional plan for accountants and students",
        "tier_description_fr": "Plan professionnel pour comptables et étudiants",
        "messages_per_day": 100,
        "messages_per_month": 3_000,
        "tokens_per_month": 5_000_000,
        "price_monthly": 7_000,
        "price_annual": 75_600,
        "has_document_sourcing": True,
        "has_pdf_generation": True,
        "has_priority_support": False,
        "has_custom_training": False,
        "has_api_access": False,
        "display_order": 2,
        "is_active": True,
        "is_visible": True,
    },
    {
        "tier_id": "max",
        "tier_name": "Max",
        "tier_name_fr": "Max",
        "tier_description": "Unlimited plan for accounting firms",
        "tier_description_fr": "Plan illimité pour cabinets comptables",
        "messages_per_day": None,
        "messages_per_month": None,
        "tokens_per_month": None,
        "price_monthly": 22_000,
        "price_annual": 237_600,
        "has_document_sourcing": True,
        "has_pdf_generation": True,
        "has_priority_support": True,
        "has_custom_training": False,
        "has_api_access": False,
        "display_order": 3,
        "is_active": True,
        "is_visible": True,
    },
    {
        "tier_id": "enterprise",
        "tier_name": "Enterprise",
        "tier_name_fr": "Entreprise",
        "tier_description": "Custom plan for large organizations",
        "tier_description_fr": "Plan sur mesure pour grandes organisations",
        "messages_per_day": None,
        "messages_per_month": None,
        "tokens_per_month": None,
        "price_monthly": 85_000,
        "price_annual": None,
        "has_document_sourcing": True,
        "has_pdf_generation": True,
        "has_priority_support": True,
        "has_custom_training": True,
        "has_api_access": True,
        "display_order": 4,
        "is_active": True,
        "is_visible": True,
    },
]


class SubscriptionService:
    """Service for subscription and quota management"""

    @staticmethod
    def ensure_default_tiers(db: Session) -> None:
        """
        Ensure the reference subscription tiers exist (self-healing seed).
        This prevents 500 errors if the table was truncated manually.
        """
        existing_ids = {
            tier_id for (tier_id,) in db.query(SubscriptionTier.tier_id).all()
        }
        missing = [tier for tier in DEFAULT_TIERS if tier["tier_id"] not in existing_ids]

        if not missing:
            return

        for tier_data in missing:
            db.add(SubscriptionTier(**tier_data))
        db.commit()

    @staticmethod
    def assign_default_subscription(db: Session, user: User) -> User:
        """
        Assign default FREE plan to a new user
        Called during registration (both local and OAuth)
        """
        user.subscription_tier = 'free'
        user.subscription_status = 'active'
        user.subscription_start_date = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_tier_config(db: Session, tier_id: str) -> Optional[SubscriptionTier]:
        """Get subscription tier configuration"""
        tier = db.query(SubscriptionTier).filter(
            SubscriptionTier.tier_id == tier_id
        ).first()
        if tier:
            return tier

        # Auto-reseed default tiers if the reference row is missing
        SubscriptionService.ensure_default_tiers(db)
        return db.query(SubscriptionTier).filter(
            SubscriptionTier.tier_id == tier_id
        ).first()

    @staticmethod
    def get_or_create_user_usage(db: Session, user_id: str, usage_date: date = None) -> UserUsage:
        """
        Get or create UserUsage record for today
        This ensures we always have a usage record to track against
        """
        if usage_date is None:
            usage_date = date.today()

        # Try to get existing record
        usage = db.query(UserUsage).filter(
            and_(
                UserUsage.user_id == user_id,
                UserUsage.usage_date == usage_date
            )
        ).first()

        # Create if doesn't exist
        if not usage:
            usage = UserUsage(
                id=str(uuid.uuid4()),
                user_id=user_id,
                usage_date=usage_date,
                messages_today=0,
                messages_this_month=0,
                tokens_this_month=0
            )
            db.add(usage)
            db.commit()
            db.refresh(usage)

        return usage

    @staticmethod
    def get_user_quota_info(db: Session, user_id: str) -> UserQuotaInfo:
        """
        Get complete quota information for a user
        This is the main method called by the dashboard and quota checks
        """
        # Get user
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Get tier configuration
        tier = SubscriptionService.get_tier_config(db, user.subscription_tier)
        if not tier:
            raise ValueError(f"Tier {user.subscription_tier} not found")

        # Get current usage
        usage = SubscriptionService.get_or_create_user_usage(db, user_id)

        # Calculate remaining quotas
        messages_remaining_today = None
        messages_remaining_month = None
        tokens_remaining_month = None

        if tier.messages_per_day is not None:
            messages_remaining_today = max(0, tier.messages_per_day - usage.messages_today)

        if tier.messages_per_month is not None:
            messages_remaining_month = max(0, tier.messages_per_month - usage.messages_this_month)

        if tier.tokens_per_month is not None:
            tokens_remaining_month = max(0, tier.tokens_per_month - usage.tokens_this_month)

        # Check if can send message
        can_send_message = True
        is_quota_exceeded = False

        # Check daily limit
        if tier.messages_per_day is not None and usage.messages_today >= tier.messages_per_day:
            can_send_message = False
            is_quota_exceeded = True

        # Check monthly limit
        if tier.messages_per_month is not None and usage.messages_this_month >= tier.messages_per_month:
            can_send_message = False
            is_quota_exceeded = True

        # Check if user needs upgrade (at 100% of quota)
        needs_upgrade = is_quota_exceeded

        # Check if at warning threshold (80% or more)
        warning_threshold_reached = False
        if tier.messages_per_day is not None:
            daily_usage_percent = (usage.messages_today / tier.messages_per_day) * 100
            if daily_usage_percent >= 80:
                warning_threshold_reached = True

        if tier.messages_per_month is not None:
            monthly_usage_percent = (usage.messages_this_month / tier.messages_per_month) * 100
            if monthly_usage_percent >= 80:
                warning_threshold_reached = True

        return UserQuotaInfo(
            user_id=user_id,
            subscription_tier=user.subscription_tier,
            subscription_status=user.subscription_status,
            tier_name=tier.tier_name,
            tier_name_fr=tier.tier_name_fr,
            messages_per_day_limit=tier.messages_per_day,
            messages_per_month_limit=tier.messages_per_month,
            tokens_per_month_limit=tier.tokens_per_month,
            messages_today=usage.messages_today,
            messages_this_month=usage.messages_this_month,
            tokens_this_month=usage.tokens_this_month,
            messages_remaining_today=messages_remaining_today,
            messages_remaining_month=messages_remaining_month,
            tokens_remaining_month=tokens_remaining_month,
            can_send_message=can_send_message,
            is_quota_exceeded=is_quota_exceeded,
            needs_upgrade=needs_upgrade,
            warning_threshold_reached=warning_threshold_reached,
            usage_date=usage.usage_date,
            subscription_start_date=user.subscription_start_date,
            subscription_end_date=user.subscription_end_date
        )

    @staticmethod
    def increment_usage(
        db: Session,
        user_id: str,
        messages: int = 1,
        tokens: int = 0
    ) -> UserUsage:
        """
        Increment user usage counters
        Called after successful message processing
        Uses row-level locking for ACID compliance
        """
        # Get or create usage record with row lock
        usage = db.query(UserUsage).filter(
            and_(
                UserUsage.user_id == user_id,
                UserUsage.usage_date == date.today()
            )
        ).with_for_update().first()

        if not usage:
            usage = UserUsage(
                id=str(uuid.uuid4()),
                user_id=user_id,
                usage_date=date.today(),
                messages_today=0,
                messages_this_month=0,
                tokens_this_month=0
            )
            db.add(usage)

        # Increment counters
        usage.messages_today += messages
        usage.messages_this_month += messages
        usage.tokens_this_month += tokens
        usage.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(usage)

        return usage

    @staticmethod
    def log_usage_event(
        db: Session,
        user_id: str,
        event_type: str,
        messages_count: int = None,
        tokens_count: int = None,
        quota_tier: str = None,
        quota_status: str = None,
        request_ip: str = None,
        user_agent: str = None,
        event_metadata: dict = None
    ) -> UsageLog:
        """
        Create an audit log entry for usage events
        """
        log = UsageLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type=event_type,
            event_timestamp=datetime.utcnow(),
            messages_count=messages_count,
            tokens_count=tokens_count,
            quota_tier=quota_tier,
            quota_status=quota_status,
            request_ip=request_ip,
            user_agent=user_agent,
            event_metadata=event_metadata
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        return log

    @staticmethod
    def reset_daily_quotas(db: Session) -> int:
        """
        Reset daily quotas for all users
        Called by cron job at midnight UTC
        Returns number of users reset
        """
        count = db.query(UserUsage).filter(
            UserUsage.usage_date < date.today()
        ).update({
            "messages_today": 0
        })
        db.commit()
        return count

    @staticmethod
    def reset_monthly_quotas(db: Session, target_month: date = None) -> int:
        """
        Reset monthly quotas for all users
        Called by cron job on the 1st of each month
        Returns number of users reset
        """
        if target_month is None:
            # Get first day of current month
            today = date.today()
            target_month = date(today.year, today.month, 1)

        count = db.query(UserUsage).filter(
            UserUsage.usage_date < target_month
        ).update({
            "messages_this_month": 0,
            "tokens_this_month": 0
        })
        db.commit()
        return count

    @staticmethod
    def upgrade_subscription(
        db: Session,
        user_id: str,
        target_tier: str,
        annual_billing: bool = False
    ) -> Tuple[bool, str, User]:
        """
        Upgrade user subscription to a higher tier
        Returns (success, message, updated_user)
        """
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return False, "User not found", None

        # Verify tier exists
        tier = SubscriptionService.get_tier_config(db, target_tier)
        if not tier:
            return False, f"Tier {target_tier} not found", None

        # Update subscription
        user.subscription_tier = target_tier
        user.subscription_status = 'active'
        user.subscription_start_date = datetime.utcnow()

        # Set end date if annual billing
        if annual_billing:
            user.subscription_end_date = datetime.utcnow() + timedelta(days=365)
        else:
            user.subscription_end_date = datetime.utcnow() + timedelta(days=30)

        db.commit()
        db.refresh(user)

        # Log the upgrade
        SubscriptionService.log_usage_event(
            db,
            user_id=user_id,
            event_type='subscription_upgraded',
            quota_tier=target_tier,
            quota_status='active',
            event_metadata={
                'previous_tier': user.subscription_tier,
                'new_tier': target_tier,
                'annual_billing': annual_billing
            }
        )

        return True, f"Upgraded to {tier.tier_name}", user

    @staticmethod
    def get_all_tiers(db: Session, visible_only: bool = True) -> list[SubscriptionTier]:
        """
        Get all subscription tiers for pricing page
        """
        # Make sure at least the default tiers exist
        SubscriptionService.ensure_default_tiers(db)

        query = db.query(SubscriptionTier).filter(SubscriptionTier.is_active == True)

        if visible_only:
            query = query.filter(SubscriptionTier.is_visible == True)

        return query.order_by(SubscriptionTier.display_order).all()
