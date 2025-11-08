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
    requested_source_count: Optional[int]  # Explicitly requested number of sources


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

        # Import legal retriever for enhanced legal searches
        from src.rag.retriever.legal_retriever import get_legal_retriever
        self.legal_retriever = get_legal_retriever()

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Construct LangGraph workflow with enhanced legal intents"""
        workflow = StateGraph(WorkflowState)

        # Nodes
        workflow.add_node("load_context", self._load_context_node)
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("direct_response", self._direct_response_node)
        workflow.add_node("retrieve_and_generate", self._retrieve_and_generate_node)
        workflow.add_node("ask_clarification", self._ask_clarification_node)
        workflow.add_node("document_sourcing", self._document_sourcing_node)
        workflow.add_node("legal_reference_search", self._legal_reference_search_node)  # NOUVEAU
        workflow.add_node("case_law_research", self._case_law_research_node)  # NOUVEAU

        # Edges
        workflow.set_entry_point("load_context")
        workflow.add_edge("load_context", "classify_intent")

        # Conditional routing basé sur l'intention (enrichi avec nouveaux intents)
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_by_intent,
            {
                "direct_response": "direct_response",
                "retrieve_and_generate": "retrieve_and_generate",
                "ask_clarification": "ask_clarification",
                "document_sourcing": "document_sourcing",
                "legal_reference_search": "legal_reference_search",  # NOUVEAU
                "case_law_research": "case_law_research"  # NOUVEAU
            }
        )

        # Tous les paths finissent au END
        workflow.add_edge("direct_response", END)
        workflow.add_edge("retrieve_and_generate", END)
        workflow.add_edge("ask_clarification", END)
        workflow.add_edge("document_sourcing", END)
        workflow.add_edge("legal_reference_search", END)  # NOUVEAU
        workflow.add_edge("case_law_research", END)  # NOUVEAU

        return workflow.compile()

    async def _load_context_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Load conversation context, check limits, and extract requested source count"""
        logger.info("workflow_node_load_context",
                   query=state["query"][:100],
                   conversation_id=state["conversation_id"])

        try:
            import uuid
            db = state.get("db_session")

            # Extract requested source count from query
            requested_count = self.rag_pipeline._extract_requested_source_count(state["query"])
            if requested_count:
                state["requested_source_count"] = requested_count
                logger.info("user_requested_specific_source_count", count=requested_count)

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

    def _route_by_intent(self, state: WorkflowState) -> Literal["direct_response", "retrieve_and_generate", "ask_clarification", "document_sourcing", "legal_reference_search", "case_law_research"]:
        """Conditional edge: Route based on intent (enriched with legal intents)"""
        intent = state.get("intent")

        if not intent:
            logger.warning("workflow_no_intent_defaulting_to_rag")
            return "retrieve_and_generate"

        logger.info("workflow_routing", intent_type=intent.intent_type, confidence=intent.confidence)

        if intent.intent_type == "general_conversation":
            return "direct_response"
        elif intent.intent_type == "clarification":
            return "ask_clarification"
        elif intent.intent_type == "document_sourcing":
            return "document_sourcing"
        elif intent.intent_type == "legal_reference_search":  # NOUVEAU
            return "legal_reference_search"
        elif intent.intent_type == "case_law_research":  # NOUVEAU
            return "case_law_research"
        else:  # rag_query (default)
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
                requested_count = state.get("requested_source_count")
                documents = await self.rag_pipeline.hybrid_retriever.retrieve(
                    query=state["query"],
                    top_k=settings.rag_rerank_top_k,
                    use_reranking=True,
                    requested_count=requested_count
                )

                state["documents"] = documents
                state["metadata"]["num_sources"] = len(documents)
                state["metadata"]["retrieval_performed"] = True

                # Format document context
                doc_context = self.rag_pipeline._format_context(documents)
                sources = self.rag_pipeline._convert_to_source_documents_enriched(documents)
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

    async def _document_sourcing_node(self, state: WorkflowState) -> WorkflowState:
        """
        Node: Document sourcing - Search and list documents by topic/keywords
        Returns a structured list of sources without full RAG generation
        """
        logger.info("workflow_node_document_sourcing", query=state["query"][:100])

        try:
            from src.config import settings
            import json

            # Extract keywords from intent's direct_answer
            intent = state.get("intent")
            keywords = []
            category_filter = None

            if intent and intent.direct_answer:
                try:
                    # Handle both dict and JSON string for direct_answer
                    if isinstance(intent.direct_answer, dict):
                        sourcing_info = intent.direct_answer
                    else:
                        sourcing_info = json.loads(intent.direct_answer)

                    keywords = sourcing_info.get("keywords", [])
                    category_filter = sourcing_info.get("category_filter")
                except (json.JSONDecodeError, TypeError, AttributeError) as e:
                    # Fallback: use query directly if parsing fails
                    logger.warning("workflow_sourcing_json_parse_failed",
                                 direct_answer=str(intent.direct_answer)[:100],
                                 error=str(e))
                    keywords = [state["query"]]
            else:
                keywords = [state["query"]]

            logger.info("workflow_sourcing_keywords_extracted", keywords=keywords, category_filter=category_filter)

            # Retrieve documents for all keywords (more results for sourcing)
            all_documents = []
            for keyword in keywords:
                documents = await self.rag_pipeline.hybrid_retriever.retrieve(
                    query=keyword,
                    top_k=settings.rag_rerank_top_k,  # Use same limit as regular RAG
                    use_reranking=True
                )
                all_documents.extend(documents)

            # Filter by category if specified
            if category_filter:
                all_documents = [
                    doc for doc in all_documents
                    if doc.get("metadata", {}).get("category") == category_filter
                ]

            # Deduplicate by file_path
            seen_paths = set()
            unique_documents = []
            for doc in all_documents:
                file_path = doc.get("metadata", {}).get("file_path")
                if file_path and file_path not in seen_paths:
                    seen_paths.add(file_path)
                    unique_documents.append(doc)

            # Sort by score
            unique_documents.sort(key=lambda x: x.get("score", 0.0), reverse=True)

            # Group by category for structured presentation
            # Apply same max limit as regular RAG (respects dynamic filtering)
            max_docs = getattr(settings, 'rag_max_documents', 8)
            docs_by_category = {}
            for doc in unique_documents[:max_docs]:  # Respect max documents limit
                metadata = doc.get("metadata", {})
                category = metadata.get("category", "general")

                if category not in docs_by_category:
                    docs_by_category[category] = []

                docs_by_category[category].append(doc)

            # Format sourcing response
            answer_parts = [
                f"J'ai trouvé **{len(unique_documents)} document(s)** pertinent(s) sur ce sujet :\n"
            ]

            # Category labels in French
            category_labels = {
                "acte_uniforme": "📜 Actes Uniformes",
                "plan_comptable": "📊 Plan Comptable OHADA",
                "doctrine": "📚 Doctrine",
                "jurisprudence": "⚖️ Jurisprudence",
                "general": "📄 Documents Généraux"
            }

            # Format documents by category
            for category, docs in docs_by_category.items():
                label = category_labels.get(category, category.replace("_", " ").title())
                answer_parts.append(f"\n### {label} ({len(docs)} document(s))")

                for i, doc in enumerate(docs[:10], 1):  # Max 10 per category
                    title = self.rag_pipeline._generate_title_from_path(
                        doc.get("metadata", {}).get("file_path", ""),
                        doc.get("metadata", {})
                    )
                    score = doc.get("score", 0.0)
                    answer_parts.append(f"{i}. **{title}** (pertinence: {score:.2f})")

            answer_parts.append(
                "\n\n💡 *Tu peux me demander des détails sur un document spécifique ou poser une question précise sur le sujet.*"
            )

            state["answer"] = "\n".join(answer_parts)

            # Convert to enriched sources
            sources = self.rag_pipeline._convert_to_source_documents_enriched(unique_documents[:30])
            state["sources"] = sources

            state["metadata"]["num_sources"] = len(unique_documents)
            state["metadata"]["sourcing_mode"] = True
            state["metadata"]["categories_found"] = list(docs_by_category.keys())
            state["metadata"]["retrieval_performed"] = True
            state["metadata"]["keywords_used"] = keywords

            logger.info("workflow_document_sourcing_complete",
                       num_documents=len(unique_documents),
                       num_categories=len(docs_by_category))

        except Exception as e:
            logger.error("workflow_document_sourcing_failed", error=str(e))
            state["error"] = f"Document sourcing failed: {str(e)}"
            state["answer"] = "Désolé, je n'ai pas pu rechercher les documents sur ce sujet."
            state["sources"] = []
            state["metadata"]["sourcing_mode"] = True
            state["metadata"]["num_sources"] = 0

        return state

    async def _legal_reference_search_node(self, state: WorkflowState) -> WorkflowState:
        """
        Node: Recherche par référence juridique précise
        Utilise LegalRetriever pour recherche ciblée
        """
        logger.info("workflow_node_legal_reference_search", query=state["query"][:100])

        try:
            from src.config import settings

            intent = state.get("intent")
            legal_metadata = intent.legal_metadata if intent else None

            if not legal_metadata or not legal_metadata.legal_references:
                # Fallback to standard RAG if no references found
                logger.warning("legal_reference_search_no_references_fallback_to_rag")
                return await self._retrieve_and_generate_node(state)

            # Extract first legal reference
            ref_text = legal_metadata.legal_references[0]
            logger.info("legal_reference_search_targeting", reference=ref_text)

            # Parse reference
            from src.rag.agents.reference_parser import get_reference_parser
            parser = get_reference_parser()
            parsed_refs = parser.parse(ref_text)

            if not parsed_refs:
                # Fallback if parsing fails
                logger.warning("legal_reference_search_parse_failed_fallback")
                return await self._retrieve_and_generate_node(state)

            # Retrieve by reference
            documents = await self.legal_retriever.retrieve_by_reference(
                reference=parsed_refs[0],
                top_k=settings.rag_rerank_top_k
            )

            state["documents"] = documents
            state["metadata"]["num_sources"] = len(documents)
            state["metadata"]["retrieval_performed"] = True
            state["metadata"]["retrieval_type"] = "legal_reference_search"
            state["metadata"]["target_reference"] = ref_text

            # Format document context
            doc_context = self.rag_pipeline._format_context(documents)
            sources = self.rag_pipeline._convert_to_source_documents_enriched(documents)

            # Generate response
            system_prompt = self.rag_pipeline._prepare_system_prompt()
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

            logger.info("workflow_legal_reference_search_complete",
                       num_documents=len(documents))

        except Exception as e:
            logger.error("workflow_legal_reference_search_failed", error=str(e))
            state["error"] = f"Legal reference search failed: {str(e)}"
            state["answer"] = "Désolé, je n'ai pas trouvé cette référence juridique dans ma base."
            state["sources"] = []

        return state

    async def _case_law_research_node(self, state: WorkflowState) -> WorkflowState:
        """
        Node: Recherche jurisprudentielle approfondie
        Filtre par type "jurisprudence" et juridiction si spécifiée
        """
        logger.info("workflow_node_case_law_research", query=state["query"][:100])

        try:
            from src.config import settings

            intent = state.get("intent")
            legal_metadata = intent.legal_metadata if intent else None

            jurisdiction = legal_metadata.jurisdiction if legal_metadata else None

            logger.info("case_law_research_filtering",
                       jurisdiction=jurisdiction)

            # Retrieve case law
            documents = await self.legal_retriever.retrieve_case_law(
                topic=state["query"],
                jurisdiction=jurisdiction,
                top_k=settings.rag_rerank_top_k
            )

            state["documents"] = documents
            state["metadata"]["num_sources"] = len(documents)
            state["metadata"]["retrieval_performed"] = True
            state["metadata"]["retrieval_type"] = "case_law_research"
            state["metadata"]["jurisdiction_filter"] = jurisdiction

            if not documents:
                state["answer"] = f"Je n'ai pas trouvé de jurisprudence{' de la ' + jurisdiction if jurisdiction else ''} sur ce sujet dans ma base de données."
                state["sources"] = []
                state["metadata"]["no_results"] = True
                return state

            # Format document context
            doc_context = self.rag_pipeline._format_context(documents)
            sources = self.rag_pipeline._convert_to_source_documents_enriched(documents)

            # Generate response with case law focus
            system_prompt = self.rag_pipeline._prepare_system_prompt()
            user_prompt = f"""{doc_context}

QUESTION DE L'UTILISATEUR:
{state["query"]}

INSTRUCTIONS SPÉCIALES POUR RECHERCHE JURISPRUDENTIELLE:
Tu réponds à une demande de recherche jurisprudentielle. Structure ta réponse ainsi :

1. **Résumé** : Nombre et types de jurisprudences trouvées
2. **Analyse par décision** : Pour chaque jurisprudence importante, indique :
   - Le titre exact (juridiction, date, référence)
   - Le principe juridique dégagé
   - L'extrait pertinent
3. **Synthèse** : Tendance jurisprudentielle générale sur le sujet

Utilise UNIQUEMENT les titres exacts des sources (pas de [Document X]).
"""

            # Check if legal report generation is enabled (Phase 2)
            if settings.enable_legal_reports and len(documents) >= settings.report_auto_generate_threshold:
                # Generate structured legal report
                logger.info("generating_legal_report", num_documents=len(documents))

                from src.rag.agents.legal_report_generator import get_report_generator
                report_generator = get_report_generator()

                report = await report_generator.generate_jurisprudence_report(
                    query=state["query"],
                    documents=documents,
                    jurisdiction=jurisdiction
                )

                # Format report as text
                state["answer"] = report_generator.format_report_as_text(report)
                state["metadata"]["report_generated"] = True
                state["metadata"]["report_type"] = report.report_type
                state["metadata"]["model_used"] = report.metadata.get("model_used")
                state["metadata"]["tokens_used"] = report.metadata.get("tokens_used")
            else:
                # Standard generation (existing logic)
                llm_response = await self.rag_pipeline.llm_client.generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.3,
                    max_tokens=2500
                )

                state["answer"] = llm_response["content"]
                state["metadata"]["model_used"] = llm_response["model"]
                state["metadata"]["tokens_used"] = llm_response["tokens_used"]
                state["metadata"]["report_generated"] = False

            state["sources"] = sources

            logger.info("workflow_case_law_research_complete",
                       num_jurisprudences=len(documents),
                       report_generated=state["metadata"].get("report_generated", False))

        except Exception as e:
            logger.error("workflow_case_law_research_failed", error=str(e))
            state["error"] = f"Case law research failed: {str(e)}"
            state["answer"] = "Désolé, je n'ai pas pu effectuer la recherche jurisprudentielle."
            state["sources"] = []

        return state

    async def execute(
        self,
        query: str,
        conversation_id: str,
        db_session: Optional[Session] = None,
        metadata: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Execute workflow and return final response

        Args:
            query: User question
            conversation_id: Conversation ID
            db_session: Optional database session for context retrieval
            metadata: Optional initial metadata

        Returns:
            Dict with answer, sources, and metadata
        """
        logger.info("workflow_execute_start", query=query[:100], conversation_id=conversation_id)

        # Initialize state
        initial_state: WorkflowState = {
            "query": query,
            "conversation_id": conversation_id,
            "db_session": db_session,
            "intent": None,
            "conversation_context": None,
            "context_info": None,
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
                requested_count = metadata.get("requested_source_count")
                documents = await self.rag_pipeline.hybrid_retriever.retrieve(
                    query=query,
                    top_k=settings.rag_rerank_top_k,
                    use_reranking=True,
                    requested_count=requested_count
                )
                retrieval_time = time.time() - retrieval_start

                # Send sources first
                sources = self.rag_pipeline._convert_to_source_documents_enriched(documents)
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

        elif intent.intent_type == "document_sourcing":
            # Document sourcing mode
            logger.info("workflow_document_sourcing_stream")

            # Execute document_sourcing node
            initial_state = {
                "query": query,
                "conversation_id": conversation_id,
                "db_session": db_session,
                "intent": intent,
                "conversation_context": conversation_context,
                "context_info": context_info.to_dict() if context_info else None,
                "documents": None,
                "answer": None,
                "sources": None,
                "metadata": metadata or {},
                "error": None
            }

            sourcing_state = await self._document_sourcing_node(initial_state)

            # Send enriched sources first
            yield {
                "type": "sources",
                "sources": sourcing_state.get("sources", []),
                "metadata": {
                    "retrieval_time_ms": 0,
                    "num_sources": len(sourcing_state.get("sources", [])),
                    "sourcing_mode": True,
                    "categories_found": sourcing_state.get("metadata", {}).get("categories_found", [])
                }
            }

            # Stream the formatted answer
            answer = sourcing_state.get("answer", "Aucun document trouvé.")
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
                    "latency_ms": int(total_time * 1000),
                    "intent_type": "document_sourcing",
                    "sourcing_mode": True,
                    "num_documents_found": sourcing_state.get("metadata", {}).get("num_sources", 0),
                    "keywords_used": sourcing_state.get("metadata", {}).get("keywords_used", []),
                    "categories_found": sourcing_state.get("metadata", {}).get("categories_found", [])
                }
            }

        elif intent.intent_type == "legal_reference_search":
            logger.info("workflow_legal_reference_stream")

            initial_state = {
                "query": query,
                "conversation_id": conversation_id,
                "db_session": db_session,
                "intent": intent,
                "conversation_context": conversation_context,
                "context_info": context_info.to_dict() if context_info else None,
                "documents": None,
                "answer": None,
                "sources": None,
                "metadata": metadata or {},
                "error": None
            }

            reference_state = await self._legal_reference_search_node(initial_state)

            sources = reference_state.get("sources", [])
            meta = reference_state.get("metadata", {})

            yield {
                "type": "sources",
                "sources": sources,
                "metadata": {
                    "retrieval_time_ms": meta.get("retrieval_time_ms", 0),
                    "num_sources": len(sources),
                    "retrieval_type": meta.get("retrieval_type", "legal_reference_search"),
                    "target_reference": meta.get("target_reference")
                }
            }

            answer = reference_state.get("answer", "Aucune référence trouvée.")
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
                    "latency_ms": int(total_time * 1000),
                    "intent_type": "legal_reference_search",
                    "num_sources": meta.get("num_sources", len(sources)),
                    "target_reference": meta.get("target_reference"),
                    "retrieval_type": meta.get("retrieval_type", "legal_reference_search"),
                    "model_used": meta.get("model_used"),
                    "tokens_used": meta.get("tokens_used")
                }
            }

        elif intent.intent_type == "case_law_research":
            logger.info("workflow_case_law_stream")

            initial_state = {
                "query": query,
                "conversation_id": conversation_id,
                "db_session": db_session,
                "intent": intent,
                "conversation_context": conversation_context,
                "context_info": context_info.to_dict() if context_info else None,
                "documents": None,
                "answer": None,
                "sources": None,
                "metadata": metadata or {},
                "error": None
            }

            case_law_state = await self._case_law_research_node(initial_state)
            sources = case_law_state.get("sources", [])
            meta = case_law_state.get("metadata", {})

            yield {
                "type": "sources",
                "sources": sources,
                "metadata": {
                    "retrieval_time_ms": meta.get("retrieval_time_ms", 0),
                    "num_sources": len(sources),
                    "retrieval_type": meta.get("retrieval_type", "case_law_research"),
                    "jurisdiction_filter": meta.get("jurisdiction_filter")
                }
            }

            answer = case_law_state.get("answer", "Je n'ai trouvé aucune jurisprudence correspondante.")
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
                    "latency_ms": int(total_time * 1000),
                    "intent_type": "case_law_research",
                    "num_sources": meta.get("num_sources", len(sources)),
                    "retrieval_type": meta.get("retrieval_type", "case_law_research"),
                    "jurisdiction_filter": meta.get("jurisdiction_filter"),
                    "model_used": meta.get("model_used"),
                    "tokens_used": meta.get("tokens_used"),
                    "report_generated": meta.get("report_generated", False),
                    "report_type": meta.get("report_type")
                }
            }

        logger.info("workflow_execute_stream_complete", intent_type=intent.intent_type)
