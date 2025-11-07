"""
Test script for document sourcing functionality
Tests the new document_sourcing intent and workflow
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.rag.agents.intent_classifier import get_intent_classifier
from src.rag.agents.rag_workflow import RAGWorkflow
from src.rag.pipeline.rag_pipeline import get_rag_pipeline


async def test_intent_classification():
    """Test intent classification for sourcing queries"""
    print("=" * 80)
    print("TEST 1: Intent Classification for Document Sourcing")
    print("=" * 80)

    classifier = get_intent_classifier()

    test_queries = [
        "Dans quels documents parle-t-on des amortissements ?",
        "Existe-t-il une jurisprudence sur la comptabilité des stocks ?",
        "Quels documents traitent des provisions ?",
        "Liste-moi les actes uniformes sur le droit commercial",
        "Où puis-je trouver des infos sur les immobilisations ?",
        # Contrôle: ces queries ne devraient PAS être classées en document_sourcing
        "C'est quoi un amortissement ?",  # Should be rag_query
        "Bonjour",  # Should be general_conversation
    ]

    for query in test_queries:
        print(f"\n📝 Query: {query}")
        intent, metadata = await classifier.classify_intent(query)
        print(f"   Intent: {intent.intent_type}")
        print(f"   Confidence: {intent.confidence:.2f}")
        print(f"   Reasoning: {intent.reasoning}")
        if intent.direct_answer:
            print(f"   Direct Answer: {intent.direct_answer[:100]}...")

    print("\n" + "=" * 80)


async def test_sourcing_workflow():
    """Test full document sourcing workflow"""
    print("\n" + "=" * 80)
    print("TEST 2: Document Sourcing Workflow (Non-Streaming)")
    print("=" * 80)

    rag_pipeline = get_rag_pipeline()
    workflow = RAGWorkflow(rag_pipeline)

    test_queries = [
        "Dans quels documents parle-t-on des amortissements ?",
        "Existe-t-il des documents sur les provisions ?",
    ]

    for query in test_queries:
        print(f"\n📝 Query: {query}")
        print("-" * 80)

        result = await workflow.execute(
            query=query,
            conversation_id="test-conv-123",
            metadata={}
        )

        print(f"✅ Answer:\n{result['answer']}\n")
        print(f"📚 Number of sources: {len(result.get('sources', []))}")
        print(f"🎯 Intent type: {result['metadata'].get('intent_type')}")
        print(f"📊 Sourcing mode: {result['metadata'].get('sourcing_mode', False)}")
        print(f"🏷️  Categories found: {result['metadata'].get('categories_found', [])}")
        print(f"🔑 Keywords used: {result['metadata'].get('keywords_used', [])}")

        # Show first 3 sources
        if result.get('sources'):
            print("\n📄 Sample sources:")
            for i, source in enumerate(result['sources'][:3], 1):
                print(f"   {i}. {source.title}")
                print(f"      Score: {source.score:.3f}")
                print(f"      Category: {source.category}")
                print(f"      File: {source.file_path}")

    print("\n" + "=" * 80)


async def test_sourcing_streaming():
    """Test document sourcing with streaming"""
    print("\n" + "=" * 80)
    print("TEST 3: Document Sourcing Workflow (Streaming)")
    print("=" * 80)

    rag_pipeline = get_rag_pipeline()
    workflow = RAGWorkflow(rag_pipeline)

    query = "Dans quels documents parle-t-on des créances ?"
    print(f"\n📝 Query: {query}")
    print("-" * 80)

    sources_received = []
    answer_chunks = []
    final_metadata = {}

    async for chunk in workflow.execute_stream(
        query=query,
        conversation_id="test-conv-456",
        db_session=None,
        metadata={}
    ):
        if chunk["type"] == "sources":
            sources_received = chunk.get("sources", [])
            print(f"📚 Received {len(sources_received)} sources")

        elif chunk["type"] == "token":
            answer_chunks.append(chunk["content"])
            # Print without newline to show streaming
            print(chunk["content"], end="", flush=True)

        elif chunk["type"] == "done":
            final_metadata = chunk.get("metadata", {})
            print("\n")
            print(f"\n✅ Streaming complete")
            print(f"🎯 Intent type: {final_metadata.get('intent_type')}")
            print(f"📊 Sourcing mode: {final_metadata.get('sourcing_mode', False)}")
            print(f"🏷️  Categories found: {final_metadata.get('categories_found', [])}")
            print(f"⏱️  Latency: {final_metadata.get('latency_ms', 0)}ms")

    print("\n" + "=" * 80)


async def main():
    """Run all tests"""
    print("\n🚀 Starting Document Sourcing Tests\n")

    try:
        # Test 1: Intent classification
        await test_intent_classification()

        # Test 2: Full workflow (non-streaming)
        await test_sourcing_workflow()

        # Test 3: Streaming workflow
        await test_sourcing_streaming()

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
