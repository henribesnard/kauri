"""
Scheduled task to cleanup orphaned conversations
Runs daily to remove conversations for deleted users
"""
import asyncio
import structlog
import httpx
from sqlalchemy import select, func
from typing import Set
import uuid

from src.config import settings
from src.models.database import SessionLocal
from src.models.conversation import Conversation

logger = structlog.get_logger()


async def verify_user_exists(user_id: uuid.UUID) -> bool:
    """
    Verify if a user exists in User Service

    Args:
        user_id: UUID of the user to verify

    Returns:
        True if user exists, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.user_service_url}/api/v1/users/{user_id}"
            )
            return response.status_code == 200
    except Exception as e:
        logger.warning("error_verifying_user", user_id=str(user_id), error=str(e))
        # En cas d'erreur, on garde le user par sécurité
        return True


async def cleanup_orphaned_conversations():
    """
    Remove conversations for users that no longer exist in User Service

    This should be run as a scheduled task (e.g., daily cron job)
    """
    logger.info("cleanup_orphaned_conversations_start")

    db = SessionLocal()
    deleted_count = 0
    verified_count = 0

    try:
        # Step 1: Get all unique user_ids from conversations
        result = db.execute(
            select(Conversation.user_id).distinct()
        )
        user_ids = [row[0] for row in result.fetchall()]

        logger.info("found_unique_users", count=len(user_ids))

        # Step 2: Verify each user exists in User Service
        orphaned_user_ids: Set[uuid.UUID] = set()

        for user_id in user_ids:
            verified_count += 1
            exists = await verify_user_exists(user_id)

            if not exists:
                logger.warning("user_no_longer_exists", user_id=str(user_id))
                orphaned_user_ids.add(user_id)

            # Rate limit API calls
            await asyncio.sleep(0.1)

        # Step 3: Delete conversations for orphaned users
        if orphaned_user_ids:
            for user_id in orphaned_user_ids:
                # Get count before deletion for logging
                count = db.query(func.count(Conversation.id)).filter(
                    Conversation.user_id == user_id
                ).scalar()

                # Delete conversations (cascade deletes messages and tags)
                db.query(Conversation).filter(
                    Conversation.user_id == user_id
                ).delete()

                deleted_count += count
                logger.info("deleted_orphaned_conversations",
                          user_id=str(user_id),
                          conversations_deleted=count)

            db.commit()

        logger.info("cleanup_orphaned_conversations_complete",
                   users_verified=verified_count,
                   orphaned_users_found=len(orphaned_user_ids),
                   conversations_deleted=deleted_count)

        return {
            "users_verified": verified_count,
            "orphaned_users": len(orphaned_user_ids),
            "conversations_deleted": deleted_count
        }

    except Exception as e:
        logger.error("cleanup_orphaned_conversations_error", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


async def cleanup_soft_deleted_messages(days_old: int = 30):
    """
    Permanently delete soft-deleted messages older than X days

    Args:
        days_old: Number of days after which to permanently delete
    """
    logger.info("cleanup_soft_deleted_messages_start", days_old=days_old)

    from datetime import datetime, timedelta
    from src.models.message import Message

    db = SessionLocal()

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Find soft-deleted messages older than cutoff
        old_deleted_messages = db.query(Message).filter(
            Message.deleted_at.isnot(None),
            Message.deleted_at < cutoff_date
        ).all()

        count = len(old_deleted_messages)

        if count > 0:
            for msg in old_deleted_messages:
                db.delete(msg)

            db.commit()
            logger.info("cleanup_soft_deleted_messages_complete",
                       messages_permanently_deleted=count)
        else:
            logger.info("no_old_soft_deleted_messages_found")

        return {"messages_deleted": count}

    except Exception as e:
        logger.error("cleanup_soft_deleted_messages_error", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # For manual testing
    asyncio.run(cleanup_orphaned_conversations())
    asyncio.run(cleanup_soft_deleted_messages(days_old=30))
