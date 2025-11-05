"""
Test script for conversation persistence functionality
Tests the complete flow: create conversation, send messages, retrieve history
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
import uuid

from src.models.database import SessionLocal, engine, Base
from src.services.conversation_service import ConversationService


def test_conversation_flow():
    """Test complete conversation flow"""
    print("=" * 80)
    print("Testing Conversation Persistence")
    print("=" * 80)

    # Create database tables
    print("\n1. Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Tables created successfully")
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        return

    # Create database session
    db: Session = SessionLocal()

    try:
        # Test 1: Create a conversation
        print("\n2. Creating a new conversation...")
        user_id = uuid.uuid4()
        conversation = ConversationService.create_conversation(
            db=db,
            user_id=user_id,
            title="Test Conversation"
        )
        print(f"✓ Created conversation: {conversation.id}")
        print(f"  - User ID: {conversation.user_id}")
        print(f"  - Title: {conversation.title}")

        # Test 2: Save user message
        print("\n3. Saving user message...")
        user_message = ConversationService.save_message(
            db=db,
            conversation_id=conversation.id,
            role="user",
            content="Qu'est-ce que le SYSCOHADA?"
        )
        print(f"✓ Saved user message: {user_message.id}")
        print(f"  - Content: {user_message.content}")

        # Test 3: Save assistant message with sources
        print("\n4. Saving assistant message with sources...")
        assistant_message = ConversationService.save_message(
            db=db,
            conversation_id=conversation.id,
            role="assistant",
            content="Le SYSCOHADA est le Système Comptable OHADA...",
            sources=[
                {"title": "Plan Comptable / Introduction", "score": 0.95},
                {"title": "Actes Uniformes / SYSCOHADA", "score": 0.89}
            ],
            metadata={
                "model_used": "deepseek/deepseek-chat",
                "tokens_used": 250,
                "latency_ms": 1500
            }
        )
        print(f"✓ Saved assistant message: {assistant_message.id}")
        print(f"  - Content preview: {assistant_message.content[:50]}...")
        print(f"  - Sources: {len(assistant_message.sources)}")
        print(f"  - Model: {assistant_message.metadata.get('model_used')}")

        # Test 4: Retrieve conversation messages
        print("\n5. Retrieving conversation messages...")
        messages = ConversationService.get_conversation_messages(
            db=db,
            conversation_id=conversation.id,
            user_id=user_id
        )
        print(f"✓ Retrieved {len(messages)} messages")
        for i, msg in enumerate(messages, 1):
            print(f"  [{i}] {msg.role}: {msg.content[:50]}...")

        # Test 5: Auto-generate title
        print("\n6. Auto-generating conversation title...")
        title = ConversationService.auto_generate_title(
            db=db,
            conversation_id=conversation.id,
            user_id=user_id
        )
        print(f"✓ Generated title: {title}")

        # Test 6: Add tags
        print("\n7. Adding tags to conversation...")
        tags = ConversationService.add_tags(
            db=db,
            conversation_id=conversation.id,
            user_id=user_id,
            tags=["comptabilité", "syscohada", "ohada"]
        )
        print(f"✓ Added {len(tags)} tags")
        for tag in tags:
            print(f"  - {tag.tag}")

        # Test 7: List user conversations
        print("\n8. Listing user conversations...")
        conversations = ConversationService.list_user_conversations(
            db=db,
            user_id=user_id,
            limit=10
        )
        print(f"✓ Found {len(conversations)} conversation(s)")
        for conv in conversations:
            print(f"  - {conv.id}: {conv.title}")
            print(f"    Messages: {len(conv.messages)}")
            print(f"    Tags: {[t.tag for t in conv.tags]}")

        # Test 8: Get conversation stats
        print("\n9. Getting conversation statistics...")
        stats = ConversationService.get_conversation_stats(
            db=db,
            user_id=user_id
        )
        print(f"✓ Statistics:")
        print(f"  - Total conversations: {stats['total_conversations']}")
        print(f"  - Active conversations: {stats['active_conversations']}")
        print(f"  - Total messages: {stats['total_messages']}")

        # Test 9: Archive conversation
        print("\n10. Archiving conversation...")
        updated_conv = ConversationService.update_conversation(
            db=db,
            conversation_id=conversation.id,
            user_id=user_id,
            is_archived=True
        )
        print(f"✓ Conversation archived: {updated_conv.is_archived}")

        # Test 10: Soft delete a message
        print("\n11. Soft deleting a message...")
        deleted = ConversationService.soft_delete_message(
            db=db,
            message_id=user_message.id,
            user_id=user_id
        )
        print(f"✓ Message deleted: {deleted}")

        # Test 11: Get messages including deleted
        print("\n12. Retrieving messages (including deleted)...")
        all_messages = ConversationService.get_conversation_messages(
            db=db,
            conversation_id=conversation.id,
            user_id=user_id,
            include_deleted=True
        )
        print(f"✓ Retrieved {len(all_messages)} messages (including deleted)")
        for msg in all_messages:
            status = " [DELETED]" if msg.deleted_at else ""
            print(f"  - {msg.role}: {msg.content[:50]}...{status}")

        print("\n" + "=" * 80)
        print("All tests completed successfully! ✓")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    test_conversation_flow()
