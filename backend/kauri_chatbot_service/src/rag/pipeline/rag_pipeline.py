"""
RAG Pipeline - Orchestrates complete RAG workflow
Combines retrieval, context preparation, and LLM generation
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
    """Complete RAG pipeline orchestrator"""

    def __init__(self):
        self.hybrid_retriever = get_hybrid_retriever()
        self.llm_client = get_llm_client()
        self.context_max_tokens = settings.context_max_tokens if hasattr(settings, 'context_max_tokens') else 3000

    def _prepare_system_prompt(self) -> str:
        """Prepare system prompt for OHADA accounting expert"""
        return """Tu es un expert-comptable spécialisé dans le droit comptable OHADA (Organisation pour l'Harmonisation en Afrique du Droit des Affaires).

Ton rôle est d'aider les utilisateurs à comprendre et appliquer les normes comptables OHADA, notamment:
- Le Système Comptable OHADA (SYSCOHADA)
- Les Actes Uniformes relatifs au droit comptable
- Les principes comptables et leur application
- Les états financiers et leur préparation
- Les traitements comptables spécifiques

Règles importantes:
1. Base tes réponses UNIQUEMENT sur les documents fournis dans le contexte
2. Si l'information n'est pas dans le contexte, dis-le clairement
3. Cite les références précises (articles, sections) quand tu réponds
4. Sois précis et professionnel dans tes explications
5. Si la question est ambiguë, demande des clarifications
6. Réponds en français, la langue officielle de l'OHADA"""

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
Réponds à la question en te basant UNIQUEMENT sur les documents fournis ci-dessus.
Si l'information n'est pas présente dans les documents, indique-le clairement.
Cite les références (articles, sections) dans ta réponse."""

    def _generate_title_from_path(self, file_path: str) -> str:
        """
        Generate structured title from file_path (version simple - tous les niveaux)

        Examples:
          /app/base_connaissances/actes_uniformes/droit comptable/titre3.docx
          -> actes_uniformes > droit comptable > titre3

          /app/base_connaissances/plan_comptable/chapitres_word/partie_1/chapitre_5.docx
          -> plan_comptable > chapitres_word > partie_1 > chapitre_5

          /app/base_connaissances/presentation_ohada/Présentation de l'OHADA.docx
          -> presentation_ohada > Présentation de l'OHADA

        Cette approche est évolutive pour supporter jurisprudence/, doctrine/, etc.
        """
        if not file_path:
            return "Document sans titre"

        # Normalize path separators and remove base prefix
        path = file_path.replace("\\", "/")
        path = path.replace("/app/base_connaissances/", "")

        # Also handle Windows absolute paths if any
        if "base_connaissances/" in path:
            path = path.split("base_connaissances/", 1)[1]

        # Remove file extension
        if "." in path:
            path = path.rsplit(".", 1)[0]

        # Split path into parts and clean
        parts = [part.strip() for part in path.split("/") if part.strip()]

        # Return hierarchical title
        return " > ".join(parts)

    def _convert_to_source_documents(self, documents: List[Dict[str, Any]]) -> List[SourceDocument]:
        """
        Convert internal document format to API schema

        Always generates title from file_path for consistency and clarity.
        This ensures all sources have hierarchical titles showing their location
        in the knowledge base (actes_uniformes, plan_comptable, jurisprudence, etc.)
        """
        sources = []
        for doc in documents:
            metadata = doc.get("metadata", {})

            # Always generate structured title from file_path
            # This ensures consistency across all document types and future additions
            file_path = metadata.get("source", "")
            title = self._generate_title_from_path(file_path)

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
        Execute complete RAG query pipeline

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
                   use_reranking=use_reranking)

        try:
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

        Yields chunks in format:
        {
            "type": "sources" | "token" | "done",
            "content": str,
            "sources": List[SourceDocument] (only for type="sources"),
            "metadata": Dict (only for type="done")
        }
        """
        start_time = time.time()

        # Generate conversation_id if not provided
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())

        logger.info("rag_pipeline_query_stream_start",
                   query=query[:100],
                   conversation_id=conversation_id)

        try:
            # Step 1: Retrieve documents (same as non-streaming)
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
            model_used = None

            async for chunk in self.llm_client.generate_stream(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=temperature or settings.llm_temperature,
                max_tokens=max_tokens or settings.llm_max_tokens,
                use_fallback=use_fallback
            ):
                token_count += 1
                if "model" in chunk:
                    model_used = chunk["model"]

                yield {
                    "type": "token",
                    "content": chunk.get("content", "")
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
            # Send error chunk
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
