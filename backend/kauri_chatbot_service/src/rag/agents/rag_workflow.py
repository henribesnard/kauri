"""
RAG Workflow with LangGraph - Orchestrates intent-based routing with conversation context
"""
from typing import TypedDict, Annotated, Literal, AsyncGenerator, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from sqlalchemy.orm import Session
import structlog
from src.rag.agents.intent_classifier import get_intent_classifier, IntentClassification
from src.services.context_manager import context_manager

logger = structlog.get_logger()


class WorkflowState(TypedDict):
    """État du workflow RAG"""
    query: str
    conversation_id: str
    db_session: Optional[Session]  # For context retrieval
    intent: IntentClassification | None
    conversation_context: list[Dict[str, Any]] | None  # Previous messages
    context_info: Dict[str, Any] | None  # Context limits info
    documents: list[Dict[str, Any]] | None
    answer: str | None
    sources: list[Any] | None
    metadata: Dict[str, Any]
    error: str | None


class RAGWorkflow:
    """
    Workflow LangGraph orchestrant le pipeline RAG avec routing intelligent

    Flow:
    1. classify_intent -> Détermine l'intention (general/rag/clarification)
    2. route_by_intent -> Route vers le bon handler
       - general_conversation -> direct_response
       - rag_query -> retrieve_and_generate
       - clarification -> ask_clarification
    3. Finalisation de la réponse
    """

    def __init__(self, rag_pipeline):
        """
        Initialize workflow with RAG pipeline components

        Args:
            rag_pipeline: Instance de RAGPipeline pour accès aux composants
        """
        self.intent_classifier = get_intent_classifier()
        self.rag_pipeline = rag_pipeline
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Construct LangGraph workflow"""
        workflow = StateGraph(WorkflowState)

        # Nodes
        workflow.add_node("load_context", self._load_context_node)
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("direct_response", self._direct_response_node)
        workflow.add_node("retrieve_and_generate", self._retrieve_and_generate_node)
        workflow.add_node("ask_clarification", self._ask_clarification_node)

        # Edges
        workflow.set_entry_point("load_context")
        workflow.add_edge("load_context", "classify_intent")

        # Conditional routing basé sur l'intention
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_by_intent,
            {
                "direct_response": "direct_response",
                "retrieve_and_generate": "retrieve_and_generate",
                "ask_clarification": "ask_clarification"
            }
        )

        # Tous les paths finissent au END
        workflow.add_edge("direct_response", END)
        workflow.add_edge("retrieve_and_generate", END)
        workflow.add_edge("ask_clarification", END)

        return workflow.compile()

    async def _load_context_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Load conversation context and check limits"""
        logger.info("workflow_node_load_context",
                   query=state["query"][:100],
                   conversation_id=state["conversation_id"])

        try:
            import uuid
            db = state.get("db_session")

            if db and state["conversation_id"]:
                # Load context
                conv_id = uuid.UUID(state["conversation_id"]) if isinstance(state["conversation_id"], str) else state["conversation_id"]
                conversation_context, context_info = context_manager.get_conversation_context(
                    db=db,
                    conversation_id=conv_id,
                    include_current_query=True,
                    current_query=state["query"]
                )

                state["conversation_context"] = conversation_context
                state["context_info"] = context_info.to_dict()

                # Add context info to metadata
                state["metadata"]["context_tokens"] = context_info.total_tokens
                state["metadata"]["context_max_tokens"] = context_info.max_tokens
                state["metadata"]["context_usage_percentage"] = context_info.usage_percentage
                state["metadata"]["context_is_over_limit"] = context_info.is_over_limit
                state["metadata"]["context_is_near_limit"] = context_info.is_near_limit

                logger.info("workflow_context_loaded",
                          messages_count=len(conversation_context),
                          total_tokens=context_info.total_tokens,
                          is_over_limit=context_info.is_over_limit,
                          is_near_limit=context_info.is_near_limit)
            else:
                state["conversation_context"] = []
                state["context_info"] = None
                logger.info("workflow_no_context_no_db_session")

        except Exception as e:
            logger.error("workflow_load_context_failed", error=str(e))
            state["conversation_context"] = []
            state["context_info"] = None

        return state

    async def _classify_intent_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Classify user intent"""
        logger.info("workflow_node_classify_intent", query=state["query"][:100])

        try:
            intent, llm_metadata = await self.intent_classifier.classify_intent(state["query"])
            state["intent"] = intent
            state["metadata"]["intent_type"] = intent.intent_type
            state["metadata"]["intent_confidence"] = intent.confidence
            state["metadata"]["intent_reasoning"] = intent.reasoning
            state["metadata"]["intent_has_direct_answer"] = bool(intent.direct_answer)

            # Store LLM metadata for potential reuse
            state["metadata"]["intent_model_used"] = llm_metadata.get("model_used")
            state["metadata"]["intent_tokens_used"] = llm_metadata.get("tokens_used", 0)

        except Exception as e:
            logger.error("workflow_classify_intent_failed", error=str(e))
            state["error"] = f"Intent classification failed: {str(e)}"
            # Fallback to RAG query
            state["intent"] = IntentClassification(
                intent_type="rag_query",
                confidence=0.5,
                reasoning="Fallback after error",
                direct_answer=None
            )

        return state

    def _route_by_intent(self, state: WorkflowState) -> Literal["direct_response", "retrieve_and_generate", "ask_clarification"]:
        """Conditional edge: Route based on intent"""
        intent = state.get("intent")

        if not intent:
            logger.warning("workflow_no_intent_defaulting_to_rag")
            return "retrieve_and_generate"

        logger.info("workflow_routing", intent_type=intent.intent_type, confidence=intent.confidence)

        if intent.intent_type == "general_conversation":
            return "direct_response"
        elif intent.intent_type == "clarification":
            return "ask_clarification"
        else:  # rag_query
            return "retrieve_and_generate"

    async def _direct_response_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Generate direct response without RAG"""
        logger.info("workflow_node_direct_response", query=state["query"][:100])

        try:
            # Check if intent classifier already provided a direct answer
            intent = state.get("intent")
            if intent and intent.direct_answer:
                logger.info("workflow_using_direct_answer_from_classifier",
                           query=state["query"][:100])
                state["answer"] = intent.direct_answer
                state["sources"] = []
                state["metadata"]["model_used"] = state["metadata"].get("intent_model_used", "deepseek/deepseek-chat")
                state["metadata"]["tokens_used"] = state["metadata"].get("intent_tokens_used", 0)
                state["metadata"]["retrieval_skipped"] = True
                state["metadata"]["answer_from_classifier"] = True
            else:
                # Fallback: generate response if classifier didn't provide one
                logger.info("workflow_generating_direct_response_fallback",
                           query=state["query"][:100])
                system_prompt = self.rag_pipeline._prepare_system_prompt()
                llm_response = await self.rag_pipeline.llm_client.generate(
                    prompt=state["query"],
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=500
                )

                state["answer"] = llm_response["content"]
                state["sources"] = []
                state["metadata"]["model_used"] = llm_response["model"]
                state["metadata"]["tokens_used"] = llm_response["tokens_used"]
                state["metadata"]["retrieval_skipped"] = True
                state["metadata"]["answer_from_classifier"] = False

        except Exception as e:
            logger.error("workflow_direct_response_failed", error=str(e))
            state["error"] = f"Direct response failed: {str(e)}"
            state["answer"] = "Désolé, je n'ai pas pu traiter votre demande."

        return state

    async def _retrieve_and_generate_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Execute RAG pipeline with smart context-aware retrieval"""
        logger.info("workflow_node_retrieve_and_generate", query=state["query"][:100])

        try:
            from src.config import settings

            # Get conversation context and intent
            conversation_context = state.get("conversation_context", [])
            intent = state.get("intent")
            intent_type = intent.intent_type if intent else "rag_query"

            # Smart retrieval decision
            should_retrieve = context_manager.should_retrieve_new_documents(
                query=state["query"],
                conversation_history=conversation_context,
                intent_type=intent_type
            )

            if should_retrieve:
                # Perform new retrieval
                logger.info("workflow_performing_new_retrieval")
                documents = await self.rag_pipeline.hybrid_retriever.retrieve(
                    query=state["query"],
                    top_k=settings.rag_rerank_top_k,
                    use_reranking=True
                )

                state["documents"] = documents
                state["metadata"]["num_sources"] = len(documents)
                state["metadata"]["retrieval_performed"] = True

                # Format document context
                doc_context = self.rag_pipeline._format_context(documents)
                sources = self.rag_pipeline._convert_to_source_documents(documents)
            else:
                # Use existing context without new retrieval
                logger.info("workflow_using_existing_context")
                state["documents"] = []
                state["metadata"]["num_sources"] = 0
                state["metadata"]["retrieval_performed"] = False
                state["metadata"]["retrieval_skipped_reason"] = "follow_up_question_with_context"

                doc_context = ""
                sources = []

            # Prepare conversation context for LLM
            conv_context_str = ""
            if conversation_context:
                conv_context_str = context_manager.format_context_for_llm(
                    conversation_history=conversation_context,
                    include_sources=True
                )

            # Generate response with context
            system_prompt = self.rag_pipeline._prepare_system_prompt()

            # Build enhanced prompt with conversation context
            if conv_context_str:
                user_prompt = f"{conv_context_str}\n{self.rag_pipeline._build_user_prompt(state['query'], doc_context)}"
            else:
                user_prompt = self.rag_pipeline._build_user_prompt(state["query"], doc_context)

            llm_response = await self.rag_pipeline.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2000
            )

            state["answer"] = llm_response["content"]
            state["sources"] = sources
            state["metadata"]["model_used"] = llm_response["model"]
            state["metadata"]["tokens_used"] = llm_response["tokens_used"]
            state["metadata"]["conversation_context_used"] = len(conversation_context) > 0

        except Exception as e:
            logger.error("workflow_retrieve_and_generate_failed", error=str(e))
            state["error"] = f"RAG pipeline failed: {str(e)}"
            state["answer"] = "Désolé, je n'ai pas pu trouver d'informations pertinentes."
            state["sources"] = []

        return state

    async def _ask_clarification_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Ask user for clarification"""
        logger.info("workflow_node_ask_clarification", query=state["query"][:100])

        # Check if intent classifier already provided a clarification/recadrage message
        intent = state.get("intent")
        if intent and intent.direct_answer:
            logger.info("workflow_using_clarification_from_classifier",
                       query=state["query"][:100])
            state["answer"] = intent.direct_answer
            state["metadata"]["model_used"] = state["metadata"].get("intent_model_used", "deepseek/deepseek-chat")
            state["metadata"]["tokens_used"] = state["metadata"].get("intent_tokens_used", 0)
            state["metadata"]["answer_from_classifier"] = True
        else:
            # Fallback clarification message
            state["answer"] = """Votre question n'est pas assez précise pour que je puisse vous aider efficacement.

Pourriez-vous préciser :
- De quel sujet comptable OHADA parlez-vous ?
- Avez-vous une référence particulière (article, titre, chapitre) ?
- Quel est le contexte de votre question ?

Je suis spécialisé en comptabilité OHADA et je peux vous aider sur :
- Le Système Comptable OHADA (SYSCOHADA)
- Les Actes Uniformes
- Les traitements comptables
- Les états financiers"""
            state["metadata"]["answer_from_classifier"] = False

        state["sources"] = []
        state["metadata"]["clarification_requested"] = True

        return state

    async def execute(
        self,
        query: str,
        conversation_id: str,
        metadata: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Execute workflow and return final response

        Args:
            query: User question
            conversation_id: Conversation ID
            metadata: Optional initial metadata

        Returns:
            Dict with answer, sources, and metadata
        """
        logger.info("workflow_execute_start", query=query[:100], conversation_id=conversation_id)

        # Initialize state
        initial_state: WorkflowState = {
            "query": query,
            "conversation_id": conversation_id,
            "intent": None,
            "documents": None,
            "answer": None,
            "sources": None,
            "metadata": metadata or {},
            "error": None
        }

        # Run workflow
        final_state = await self.graph.ainvoke(initial_state)

        logger.info("workflow_execute_complete",
                   intent_type=final_state.get("intent", {}).intent_type if final_state.get("intent") else "unknown",
                   has_error=bool(final_state.get("error")))

        # Format response
        return {
            "conversation_id": conversation_id,
            "query": query,
            "answer": final_state.get("answer", "Erreur lors du traitement."),
            "sources": final_state.get("sources", []),
            "metadata": final_state.get("metadata", {})
        }

    async def execute_stream(
        self,
        query: str,
        conversation_id: str,
        db_session: Optional[Session] = None,
        metadata: Dict[str, Any] | None = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute workflow with streaming response generation

        Same logic as execute() but streams the final answer generation.
        Yields chunks in SSE format compatible with chat API.

        Args:
            query: User question
            conversation_id: Conversation ID
            db_session: Optional database session for context retrieval
            metadata: Optional initial metadata

        Yields:
            Dict with type, content, sources, metadata
        """
        logger.info("workflow_execute_stream_start", query=query[:100], conversation_id=conversation_id)

        from src.config import settings
        import time
        start_time = time.time()

        # Load conversation context if db_session available
        conversation_context = []
        context_info = None

        if db_session and conversation_id:
            try:
                import uuid
                conv_id = uuid.UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id
                conversation_context, context_info = context_manager.get_conversation_context(
                    db=db_session,
                    conversation_id=conv_id,
                    include_current_query=True,
                    current_query=query
                )
                logger.info("workflow_stream_context_loaded",
                          messages_count=len(conversation_context),
                          total_tokens=context_info.total_tokens if context_info else 0)
            except Exception as e:
                logger.error("workflow_stream_load_context_failed", error=str(e))
                conversation_context = []
                context_info = None

        # Step 1: Classify intent (same as regular workflow)
        intent, intent_metadata = await self.intent_classifier.classify_intent(query)

        logger.info("workflow_intent_classified_stream",
                   intent_type=intent.intent_type,
                   confidence=intent.confidence)

        # Step 2: Route based on intent
        if intent.intent_type == "general_conversation":
            # Direct response without retrieval
            logger.info("workflow_direct_response_stream")

            # Send empty sources first
            yield {
                "type": "sources",
                "sources": [],
                "metadata": {
                    "retrieval_time_ms": 0,
                    "num_sources": 0,
                    "retrieval_skipped": True
                }
            }

            # Check if classifier already provided answer
            if intent.direct_answer:
                # Stream the direct answer from classifier
                answer = intent.direct_answer
                for char in answer:
                    yield {
                        "type": "token",
                        "content": char
                    }

                total_time = time.time() - start_time
                yield {
                    "type": "done",
                    "metadata": {
                        "conversation_id": conversation_id,
                        "model_used": intent_metadata.get("model_used", "deepseek/deepseek-chat"),
                        "tokens_used": intent_metadata.get("tokens_used", 0),
                        "latency_ms": int(total_time * 1000),
                        "retrieval_time_ms": 0,
                        "generation_time_ms": 0,
                        "intent_type": "general_conversation",
                        "answer_from_classifier": True
                    }
                }
            else:
                # Generate response without context
                system_prompt = self.rag_pipeline._prepare_system_prompt()
                generation_start = time.time()
                token_count = 0

                async for chunk in self.rag_pipeline.llm_client.generate_stream(
                    prompt=query,
                    system_prompt=system_prompt,
                    temperature=settings.llm_temperature,
                    max_tokens=settings.llm_max_tokens
                ):
                    token_count += 1
                    yield {
                        "type": "token",
                        "content": chunk
                    }

                generation_time = time.time() - generation_start
                total_time = time.time() - start_time

                yield {
                    "type": "done",
                    "metadata": {
                        "conversation_id": conversation_id,
                        "model_used": f"{settings.llm_provider}/{settings.llm_model}",
                        "tokens_used": token_count,
                        "latency_ms": int(total_time * 1000),
                        "retrieval_time_ms": 0,
                        "generation_time_ms": int(generation_time * 1000),
                        "intent_type": "general_conversation"
                    }
                }

        elif intent.intent_type == "rag_query":
            # RAG pipeline with smart retrieval
            logger.info("workflow_rag_query_stream")

            # Smart retrieval decision
            should_retrieve = context_manager.should_retrieve_new_documents(
                query=query,
                conversation_history=conversation_context,
                intent_type=intent.intent_type
            )

            retrieval_time = 0
            if should_retrieve:
                # Perform new retrieval
                logger.info("workflow_stream_performing_new_retrieval")
                retrieval_start = time.time()
                documents = await self.rag_pipeline.hybrid_retriever.retrieve(
                    query=query,
                    top_k=settings.rag_rerank_top_k,
                    use_reranking=True
                )
                retrieval_time = time.time() - retrieval_start

                # Send sources first
                sources = self.rag_pipeline._convert_to_source_documents(documents)
                yield {
                    "type": "sources",
                    "sources": sources,
                    "metadata": {
                        "retrieval_time_ms": int(retrieval_time * 1000),
                        "num_sources": len(sources),
                        "retrieval_performed": True
                    }
                }

                # Prepare document context
                doc_context = self.rag_pipeline._format_context(documents)
            else:
                # Use existing context without new retrieval
                logger.info("workflow_stream_using_existing_context")
                yield {
                    "type": "sources",
                    "sources": [],
                    "metadata": {
                        "retrieval_time_ms": 0,
                        "num_sources": 0,
                        "retrieval_performed": False,
                        "retrieval_skipped_reason": "follow_up_question_with_context"
                    }
                }
                doc_context = ""

            # Prepare conversation context for LLM
            conv_context_str = ""
            if conversation_context:
                conv_context_str = context_manager.format_context_for_llm(
                    conversation_history=conversation_context,
                    include_sources=True
                )

            # Prepare prompts with conversation context
            system_prompt = self.rag_pipeline._prepare_system_prompt()

            # Build enhanced prompt with conversation context
            if conv_context_str:
                user_prompt = f"{conv_context_str}\n{self.rag_pipeline._build_user_prompt(query, doc_context)}"
            else:
                user_prompt = self.rag_pipeline._build_user_prompt(query, doc_context)

            # Stream generation
            generation_start = time.time()
            token_count = 0

            async for chunk in self.rag_pipeline.llm_client.generate_stream(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2000
            ):
                token_count += 1
                yield {
                    "type": "token",
                    "content": chunk
                }

            generation_time = time.time() - generation_start
            total_time = time.time() - start_time

            yield {
                "type": "done",
                "metadata": {
                    "conversation_id": conversation_id,
                    "model_used": f"{settings.llm_provider}/{settings.llm_model}",
                    "tokens_used": token_count,
                    "latency_ms": int(total_time * 1000),
                    "retrieval_time_ms": int(retrieval_time * 1000),
                    "generation_time_ms": int(generation_time * 1000),
                    "intent_type": "rag_query",
                    "use_reranking": True,
                    "retrieval_performed": should_retrieve,
                    "conversation_context_used": len(conversation_context) > 0
                }
            }

        elif intent.intent_type == "clarification":
            # Ask for clarification
            logger.info("workflow_clarification_stream")

            # Send empty sources
            yield {
                "type": "sources",
                "sources": [],
                "metadata": {
                    "retrieval_time_ms": 0,
                    "num_sources": 0,
                    "clarification_requested": True
                }
            }

            # Use direct answer from classifier if available
            if intent.direct_answer:
                answer = intent.direct_answer
                for char in answer:
                    yield {
                        "type": "token",
                        "content": char
                    }

                total_time = time.time() - start_time
                yield {
                    "type": "done",
                    "metadata": {
                        "conversation_id": conversation_id,
                        "model_used": intent_metadata.get("model_used", "deepseek/deepseek-chat"),
                        "tokens_used": intent_metadata.get("tokens_used", 0),
                        "latency_ms": int(total_time * 1000),
                        "intent_type": "clarification",
                        "answer_from_classifier": True
                    }
                }
            else:
                # Fallback clarification message
                fallback_message = """Votre question n'est pas assez précise pour que je puisse vous aider efficacement.

Pourriez-vous préciser :
- De quel sujet comptable OHADA parlez-vous ?
- Avez-vous une référence particulière (article, titre, chapitre) ?
- Quel est le contexte de votre question ?

Je suis spécialisé en comptabilité OHADA et je peux vous aider sur :
- Le Système Comptable OHADA (SYSCOHADA)
- Les Actes Uniformes
- Les traitements comptables
- Les états financiers"""

                for char in fallback_message:
                    yield {
                        "type": "token",
                        "content": char
                    }

                total_time = time.time() - start_time
                yield {
                    "type": "done",
                    "metadata": {
                        "conversation_id": conversation_id,
                        "latency_ms": int(total_time * 1000),
                        "intent_type": "clarification"
                    }
                }

        logger.info("workflow_execute_stream_complete", intent_type=intent.intent_type)
