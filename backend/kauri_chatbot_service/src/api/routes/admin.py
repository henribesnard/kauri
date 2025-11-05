"""
Admin API Routes - Maintenance and cleanup tasks
Protected endpoints for administrative operations
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import structlog

from src.auth.jwt_validator import get_current_user
from src.tasks.cleanup_orphaned_data import (
    cleanup_orphaned_conversations,
    cleanup_soft_deleted_messages
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def verify_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Verify current user is an admin
    TODO: Check user role from User Service or add admin flag to JWT
    """
    # For now, just verify user is authenticated
    # In production, add role check:
    # if current_user.get("role") != "admin":
    #     raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.post("/cleanup/orphaned-conversations")
async def run_cleanup_orphaned_conversations(
    current_user: Dict = Depends(verify_admin_user)
):
    """
    Manually trigger cleanup of orphaned conversations

    Removes conversations for users that no longer exist in User Service.
    This task should normally run as a scheduled cron job.

    Requires admin authentication.

    Returns:
        Statistics about cleanup operation
    """
    logger.info("manual_cleanup_orphaned_conversations_triggered",
               admin_user=current_user.get("email"))

    try:
        result = await cleanup_orphaned_conversations()

        logger.info("manual_cleanup_orphaned_conversations_complete",
                   result=result)

        return {
            "status": "success",
            "message": "Orphaned conversations cleanup completed",
            "stats": result
        }

    except Exception as e:
        logger.error("manual_cleanup_orphaned_conversations_error",
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )


@router.post("/cleanup/soft-deleted-messages")
async def run_cleanup_soft_deleted_messages(
    days_old: int = 30,
    current_user: Dict = Depends(verify_admin_user)
):
    """
    Permanently delete soft-deleted messages older than X days

    Args:
        days_old: Number of days threshold (default: 30)

    Requires admin authentication.

    Returns:
        Statistics about cleanup operation
    """
    logger.info("manual_cleanup_soft_deleted_messages_triggered",
               admin_user=current_user.get("email"),
               days_old=days_old)

    try:
        result = await cleanup_soft_deleted_messages(days_old=days_old)

        logger.info("manual_cleanup_soft_deleted_messages_complete",
                   result=result)

        return {
            "status": "success",
            "message": f"Soft-deleted messages older than {days_old} days permanently removed",
            "stats": result
        }

    except Exception as e:
        logger.error("manual_cleanup_soft_deleted_messages_error",
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )


@router.get("/stats/database")
async def get_database_stats(
    current_user: Dict = Depends(verify_admin_user)
):
    """
    Get database statistics for monitoring

    Requires admin authentication.

    Returns:
        Database statistics and health metrics
    """
    from sqlalchemy import func
    from src.models.database import SessionLocal
    from src.models.conversation import Conversation
    from src.models.message import Message
    from src.models.conversation_tag import ConversationTag

    db = SessionLocal()

    try:
        # Gather statistics
        total_conversations = db.query(func.count(Conversation.id)).scalar()
        active_conversations = db.query(func.count(Conversation.id)).filter(
            Conversation.is_archived == False
        ).scalar()
        archived_conversations = total_conversations - active_conversations

        total_messages = db.query(func.count(Message.id)).scalar()
        active_messages = db.query(func.count(Message.id)).filter(
            Message.deleted_at.is_(None)
        ).scalar()
        soft_deleted_messages = total_messages - active_messages

        total_tags = db.query(func.count(ConversationTag.id)).scalar()
        unique_users = db.query(func.count(func.distinct(Conversation.user_id))).scalar()

        # Average messages per conversation
        avg_messages_per_conv = db.query(
            func.avg(
                db.query(func.count(Message.id))
                .filter(Message.conversation_id == Conversation.id)
                .correlate(Conversation)
                .scalar_subquery()
            )
        ).scalar()

        return {
            "status": "healthy",
            "database": {
                "conversations": {
                    "total": total_conversations,
                    "active": active_conversations,
                    "archived": archived_conversations
                },
                "messages": {
                    "total": total_messages,
                    "active": active_messages,
                    "soft_deleted": soft_deleted_messages
                },
                "tags": {
                    "total": total_tags
                },
                "users": {
                    "unique_users_with_conversations": unique_users
                },
                "averages": {
                    "messages_per_conversation": round(avg_messages_per_conv or 0, 2)
                }
            }
        }

    except Exception as e:
        logger.error("get_database_stats_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stats: {str(e)}"
        )
    finally:
        db.close()
