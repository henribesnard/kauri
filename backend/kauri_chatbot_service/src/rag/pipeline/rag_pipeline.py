"""
RAG Pipeline - Orchestrates complete RAG workflow
Combines retrieval, context preparation, and LLM generation with intelligent intent-based routing
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
import time
import uuid
import structlog
from src.config import settings
from src.rag.retriever.hybrid_retriever import get_hybrid_retriever
from src.llm.llm_client import get_llm_client
from src.schemas.chat import SourceDocument

logger = structlog.get_logger()


class RAGPipeline:
    """
    Complete RAG pipeline orchestrator with LangGraph workflow

    New Architecture:
    - Uses LangGraph workflow for intelligent routing
    - Intent classification via LLM (more robust than static patterns)
    - Conditional routing: general_conversation | rag_query | clarification
    """

    def __init__(self, use_workflow: bool = True):
        """
        Initialize RAG Pipeline

        Args:
            use_workflow: Use LangGraph workflow for intent-based routing (default: True)
                         Set to False to use legacy direct pipeline
        """
        self.hybrid_retriever = get_hybrid_retriever()
        self.llm_client = get_llm_client()
        self.context_max_tokens = settings.context_max_tokens if hasattr(settings, 'context_max_tokens') else 3000
        self.use_workflow = use_workflow

        # Initialize workflow if enabled
        if self.use_workflow:
            from src.rag.agents.rag_workflow import RAGWorkflow
            self.workflow = RAGWorkflow(rag_pipeline=self)
            logger.info("rag_pipeline_initialized_with_workflow")
        else:
            self.workflow = None
            logger.info("rag_pipeline_initialized_legacy_mode")

    def _prepare_system_prompt(self) -> str:
        """Prepare system prompt for KAURI - OHADA accounting expert"""
        return """Tu es KAURI, assistant spécialisé en comptabilité OHADA (Organisation pour l'Harmonisation en Afrique du Droit des Affaires).

Tu aides les utilisateurs à comprendre et appliquer les normes comptables OHADA :
- Le Système Comptable OHADA (SYSCOHADA)
- Les Actes Uniformes relatifs au droit comptable
- Les principes comptables et leur application
- Les états financiers et leur préparation
- Les traitements comptables spécifiques

Règles importantes pour tes réponses :
1. Réponds de manière simple, directe et naturelle
2. Ne te présente JAMAIS comme "expert-comptable" ou "en tant qu'expert"
3. Ne dis JAMAIS "d'après les documents fournis" ou "selon les documents"
4. Commence directement par la réponse, sans formule d'introduction
5. Cite les références précises (articles, titres, chapitres) pour appuyer tes explications
6. Si une information n'est pas dans ta documentation : "Je n'ai pas cette information dans ma documentation actuelle"
7. Sois précis, clair et pédagogue
8. Réponds en français"""

    def _format_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into context string"""
        if not documents:
            return "Aucun document pertinent trouvé dans la base de connaissances."

        context_parts = ["CONTEXTE - Documents pertinents:\n"]

        for i, doc in enumerate(documents, 1):
            metadata = doc.get("metadata", {})
            content = doc.get("content", "").strip()

            # Build source reference
            source_parts = []
            if metadata.get("acte_uniforme"):
                source_parts.append(f"Acte Uniforme: {metadata['acte_uniforme']}")
            if metadata.get("livre"):
                source_parts.append(f"Livre {metadata['livre']}")
            if metadata.get("titre"):
                source_parts.append(f"Titre {metadata['titre']}")
            if metadata.get("article"):
                source_parts.append(f"Article {metadata['article']}")

            source_ref = " | ".join(source_parts) if source_parts else metadata.get("source", f"Document {i}")

            context_parts.append(f"\n[Document {i}] {source_ref}")
            context_parts.append(f"Score: {doc.get('score', 0.0):.3f}")
            context_parts.append(f"Contenu:\n{content}\n")
            context_parts.append("-" * 80)

        return "\n".join(context_parts)

    def _build_user_prompt(self, query: str, context: str) -> str:
        """Build complete user prompt with context and query"""
        return f"""{context}

QUESTION DE L'UTILISATEUR:
{query}

INSTRUCTIONS:
Réponds de manière simple et directe en utilisant les informations ci-dessus.
Ne commence PAS par "En tant qu'expert" ou "Je vous explique".
Entre directement dans le vif du sujet.
Cite les références (titres, chapitres, articles) pour appuyer tes explications.
Ne mentionne JAMAIS "les documents fournis" ou "selon les documents"."""

    def _generate_title_from_path(self, file_path: str, metadata: Dict[str, Any] = None) -> str:
        """
        Generate human-readable title from file_path and metadata

        New format examples:
          Plan Comptable : Partie 4 - Chapitre 7 : Comptes combinés
          Actes Uniformes : Droit commercial général - Titre 3 : Dispositions générales

        Args:
            file_path: Path to source file
            metadata: Optional metadata dict with category, section, title

        Returns:
            Formatted title string
        """
        if not file_path:
            return "Document sans titre"

        # Normalize path
        path = file_path.replace("\\", "/")

        # Extract filename without extension
        filename = path.split("/")[-1]
        if "." in filename:
            filename = filename.rsplit(".", 1)[0]

        # Try to extract from metadata first (from ChromaDB)
        if metadata:
            category = metadata.get("category", "")
            section = metadata.get("section", "")
            title = metadata.get("title", "")

            # Format category (capitalize and clean)
            if "plan_comptable" in category.lower():
                category_label = "Plan Comptable"
            elif "actes_uniformes" in category.lower():
                category_label = "Actes Uniformes"
            elif "presentation" in category.lower():
                category_label = "Présentation OHADA"
            else:
                category_label = category.replace("_", " ").title()

            # Format section (partie_4, droit_commercial général, etc.)
            if section:
                section_clean = section.replace("_", " ").title()
            else:
                section_clean = ""

            # Build hierarchical title with all levels
            # Format: "Actes Uniformes / Droit Commercial Général / Livre_1 Statut du commerçant"
            parts = []
            if category_label:
                parts.append(category_label)
            if section_clean:
                parts.append(section_clean)
            if title:
                # Title is now complete as-is from filename (e.g., "chapitre_1 Plan de comptes")
                parts.append(title)

            # Join with "/" separator for hierarchy
            if parts:
                return " / ".join(parts)
            else:
                return filename

        # Fallback: extract from filename
        # e.g., "chapitre_7_Comptes combinés" -> "Chapitre 7 : Comptes combinés"
        if "_" in filename:
            parts = filename.split("_", 1)
            if len(parts) == 2:
                prefix = parts[0].replace("chapitre", "Chapitre").replace("titre", "Titre")
                suffix = parts[1]
                return f"{prefix} : {suffix}"

        return filename.replace("_", " ").title()

    def _convert_to_source_documents(self, documents: List[Dict[str, Any]]) -> List[SourceDocument]:
        """
        Convert internal document format to API schema

        Generates human-readable titles with proper formatting:
        - Plan Comptable : Partie 4 - Chapitre 7 : Comptes combinés
        - Actes Uniformes : Droit commercial - Titre 3 : Dispositions
        """
        sources = []
        for doc in documents:
            metadata = doc.get("metadata", {})

            # Get file_path (stored in metadata by new ingestion)
            file_path = metadata.get("file_path", metadata.get("source", ""))

            # Generate formatted title from file_path + metadata
            title = self._generate_title_from_path(file_path, metadata)

            sources.append(SourceDocument(
                title=title,
                score=doc.get("score", 0.0)
            ))
        return sources

    async def query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_reranking: bool = True,
        use_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Execute complete RAG query pipeline with intelligent routing

        New Architecture (when use_workflow=True):
        - Uses LangGraph workflow with intent classification
        - Routes automatically to: general_conversation, rag_query, or clarification
        - More robust than static pattern matching

        Args:
            query: User question
            conversation_id: Optional conversation tracking ID
            temperature: LLM temperature (default from settings)
            max_tokens: Max tokens to generate (default from settings)
            use_reranking: Whether to use cross-encoder reranking
            use_fallback: Force use of fallback LLM

        Returns:
            Dict with answer, sources, metadata
        """
        start_time = time.time()

        # Generate conversation_id if not provided
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())

        logger.info("rag_pipeline_query_start",
                   query=query[:100],
                   conversation_id=conversation_id,
                   use_workflow=self.use_workflow)

        # Use workflow if enabled
        if self.use_workflow and self.workflow:
            try:
                result = await self.workflow.execute(
                    query=query,
                    conversation_id=conversation_id,
                    metadata={
                        "use_reranking": use_reranking,
                        "use_fallback": use_fallback
                    }
                )

                # Add timing
                total_time = time.time() - start_time
                result["latency_ms"] = int(total_time * 1000)
                result["model_used"] = result["metadata"].get("model_used", "unknown")
                result["tokens_used"] = result["metadata"].get("tokens_used", 0)

                return result

            except Exception as e:
                logger.error("workflow_execution_error", error=str(e))
                # Fallback to legacy pipeline
                logger.warning("falling_back_to_legacy_pipeline")

        # Legacy pipeline (or fallback)
        try:
            # Note: Intent classification is now handled by LangGraph workflow above
            # Legacy pipeline always does RAG retrieval for fallback cases

            # Step 1: Retrieve relevant documents
            retrieval_start = time.time()
            documents = await self.hybrid_retriever.retrieve(
                query=query,
                top_k=settings.rag_rerank_top_k if use_reranking else settings.rag_top_k,
                use_reranking=use_reranking
            )
            retrieval_time = time.time() - retrieval_start

            logger.info("rag_pipeline_retrieval_complete",
                       num_documents=len(documents),
                       retrieval_time_ms=int(retrieval_time * 1000))

            # Step 2: Prepare context and prompts
            system_prompt = self._prepare_system_prompt()
            context = self._format_context(documents)
            user_prompt = self._build_user_prompt(query, context)

            # Step 3: Generate answer with LLM
            generation_start = time.time()
            llm_response = await self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=temperature or settings.llm_temperature,
                max_tokens=max_tokens or settings.llm_max_tokens,
                use_fallback=use_fallback
            )
            generation_time = time.time() - generation_start

            total_time = time.time() - start_time

            logger.info("rag_pipeline_query_complete",
                       total_time_ms=int(total_time * 1000),
                       retrieval_time_ms=int(retrieval_time * 1000),
                       generation_time_ms=int(generation_time * 1000),
                       model_used=llm_response["model"],
                       tokens_used=llm_response["tokens_used"])

            # Step 4: Format response
            return {
                "conversation_id": conversation_id,
                "query": query,
                "answer": llm_response["content"],
                "sources": self._convert_to_source_documents(documents),
                "model_used": llm_response["model"],
                "tokens_used": llm_response["tokens_used"],
                "latency_ms": int(total_time * 1000),
                "metadata": {
                    "retrieval_time_ms": int(retrieval_time * 1000),
                    "generation_time_ms": int(generation_time * 1000),
                    "num_sources": len(documents),
                    "use_reranking": use_reranking
                }
            }

        except Exception as e:
            logger.error("rag_pipeline_query_error", error=str(e), query=query[:100])
            raise

    async def query_stream(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_reranking: bool = True,
        use_fallback: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute RAG query with streaming response

        Uses same workflow as query() with intent classification and routing.
        Only difference: streams the final answer generation.

        Yields chunks in format:
        {
            "type": "sources" | "token" | "done",
            "content": str,
            "sources": List[SourceDocument] (only for type="sources"),
            "metadata": Dict (only for type="done")
        }
        """
        # Generate conversation_id if not provided
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())

        logger.info("rag_pipeline_query_stream_start",
                   query=query[:100],
                   conversation_id=conversation_id,
                   use_workflow=self.use_workflow)

        # Use workflow if enabled (same as query())
        if self.use_workflow and self.workflow:
            try:
                async for chunk in self.workflow.execute_stream(
                    query=query,
                    conversation_id=conversation_id,
                    metadata={
                        "use_reranking": use_reranking,
                        "use_fallback": use_fallback,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                ):
                    yield chunk

            except Exception as e:
                logger.error("workflow_stream_execution_error", error=str(e))
                # Send error chunk
                yield {
                    "type": "error",
                    "content": f"Erreur lors du traitement de la requête: {str(e)}"
                }
        else:
            # Legacy fallback (workflow disabled)
            logger.warning("using_legacy_stream_pipeline")
            start_time = time.time()

            try:
                # Step 1: Retrieve documents
                retrieval_start = time.time()
                documents = await self.hybrid_retriever.retrieve(
                    query=query,
                    top_k=settings.rag_rerank_top_k if use_reranking else settings.rag_top_k,
                    use_reranking=use_reranking
                )
                retrieval_time = time.time() - retrieval_start

                logger.info("rag_pipeline_retrieval_complete_stream",
                           num_documents=len(documents),
                           retrieval_time_ms=int(retrieval_time * 1000))

                # Step 2: Send sources first
                yield {
                    "type": "sources",
                    "sources": self._convert_to_source_documents(documents),
                    "metadata": {
                        "retrieval_time_ms": int(retrieval_time * 1000),
                        "num_sources": len(documents)
                    }
                }

                # Step 3: Prepare prompts
                system_prompt = self._prepare_system_prompt()
                context = self._format_context(documents)
                user_prompt = self._build_user_prompt(query, context)

                # Step 4: Stream LLM response
                generation_start = time.time()
                token_count = 0
                model_used = f"{settings.llm_provider}/{settings.llm_model}"

                async for chunk in self.llm_client.generate_stream(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=temperature or settings.llm_temperature,
                    max_tokens=max_tokens or settings.llm_max_tokens,
                    use_fallback=use_fallback
                ):
                    token_count += 1
                    yield {
                        "type": "token",
                        "content": chunk
                    }

                generation_time = time.time() - generation_start
                total_time = time.time() - start_time

                # Step 5: Send completion metadata
                yield {
                    "type": "done",
                    "metadata": {
                        "conversation_id": conversation_id,
                        "model_used": model_used,
                        "tokens_used": token_count,
                        "latency_ms": int(total_time * 1000),
                        "retrieval_time_ms": int(retrieval_time * 1000),
                        "generation_time_ms": int(generation_time * 1000),
                        "use_reranking": use_reranking
                    }
                }

                logger.info("rag_pipeline_query_stream_complete",
                           total_time_ms=int(total_time * 1000),
                           tokens_streamed=token_count)

            except Exception as e:
                logger.error("rag_pipeline_query_stream_error", error=str(e), query=query[:100])
                yield {
                    "type": "error",
                    "content": f"Erreur lors du traitement de la requête: {str(e)}"
                }


# Singleton instance
_rag_pipeline_instance: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    """Get singleton RAG pipeline instance"""
    global _rag_pipeline_instance
    if _rag_pipeline_instance is None:
        _rag_pipeline_instance = RAGPipeline()
    return _rag_pipeline_instance
