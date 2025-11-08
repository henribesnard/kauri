"""
RAG Pipeline - Orchestrates complete RAG workflow
Combines retrieval, context preparation, and LLM generation with intelligent intent-based routing
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
import time
import uuid
import re
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

    def _extract_requested_source_count(self, query: str) -> Optional[int]:
        """
        Extract explicitly requested number of sources from user query

        Patterns detected:
        - "donne-moi 3 sources"
        - "3 sources sur..."
        - "peux-tu me donner 5 documents"
        - "montre-moi 2 exemples"

        Args:
            query: User query text

        Returns:
            Number of sources requested, or None if not specified
        """
        patterns = [
            r'(?:donne|donner|montrer|fournir|avoir|obtenir)(?:-moi| moi)?[\s]+(\d+)[\s]+(?:source|document|exemple|référence)',
            r'(\d+)[\s]+(?:source|document|exemple|référence)',
            r'(?:top|meilleur|premier)[\s]+(\d+)',
        ]

        query_lower = query.lower()

        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                count = int(match.group(1))
                if 1 <= count <= 20:  # Reasonable range
                    logger.info("extracted_requested_source_count",
                               query=query[:100],
                               requested_count=count)
                    return count

        return None

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

**Style et ton :**
1. Réponds de manière simple, directe et naturelle
2. Ne te présente JAMAIS comme "expert-comptable" ou "en tant qu'expert"
3. Commence directement par la réponse, sans formule d'introduction
4. Sois précis, clair et pédagogue
5. Réponds en français

**Citations et références (CRITIQUE) :**
6. NE DIS JAMAIS "[Document 1]", "[Document 2]", "[Document 3]", etc.
7. NE DIS JAMAIS "d'après les documents fournis" ou "selon les documents"
8. TOUJOURS citer par le titre exact de la source : "Selon le Plan Comptable OHADA : Partie X...", "D'après l'Acte Uniforme relatif à..."
9. Mentionne les articles, chapitres, titres précis pour appuyer tes explications (ex: "Article 15", "Chapitre 3")
10. Format professionnel : "Selon [Titre exact de la source], ..." ou "D'après [Titre exact], ..."

**Gestion des limites :**
11. Si une information n'est pas dans ta documentation : "Je n'ai pas cette information dans ma documentation actuelle"
12. Ne jamais inventer ou extrapoler au-delà des sources fournies"""

    def _format_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into context string with human-readable titles"""
        if not documents:
            return "Aucun document pertinent trouvé dans la base de connaissances."

        context_parts = ["CONTEXTE - Documents pertinents:\n"]

        for i, doc in enumerate(documents, 1):
            metadata = doc.get("metadata", {})
            content = doc.get("content", "").strip()

            # Generate human-readable title from file_path and metadata
            file_path = metadata.get("file_path", "")
            document_title = self._generate_title_from_path(file_path, metadata)

            # Build additional reference details (if available)
            ref_details = []
            if metadata.get("article"):
                ref_details.append(f"Article {metadata['article']}")
            if metadata.get("page"):
                ref_details.append(f"Page {metadata['page']}")

            ref_suffix = f" ({', '.join(ref_details)})" if ref_details else ""

            # Format: SOURCE N°X: [Title] (Article X, Page Y)
            context_parts.append(f"\nSOURCE N°{i}: {document_title}{ref_suffix}")
            context_parts.append(f"Pertinence: {doc.get('score', 0.0):.3f}")
            context_parts.append(f"Contenu:\n{content}\n")
            context_parts.append("-" * 80)

        return "\n".join(context_parts)

    def _build_user_prompt(self, query: str, context: str) -> str:
        """Build complete user prompt with context and query"""
        return f"""{context}

QUESTION DE L'UTILISATEUR:
{query}

INSTRUCTIONS IMPORTANTES POUR LA RÉPONSE:

1. **Citations professionnelles** :
   - NE DIS JAMAIS "[Document 1]", "[Document 2]", etc.
   - UTILISE UNIQUEMENT les titres exacts des sources (ex: "Plan Comptable OHADA : Partie 2 - Chapitre 35")
   - Format recommandé : "Selon le [Titre exact de la source], ..." ou "D'après [Titre exact], ..."
   - Exemple : "D'après le Plan Comptable OHADA : Partie 2 - Chapitre 35, ..."

2. **Style de réponse** :
   - Réponds de manière simple, directe et naturelle
   - Entre directement dans le vif du sujet
   - Ne commence PAS par "En tant qu'expert" ou "Je vous explique"
   - Ne dis JAMAIS "les documents fournis" ou "selon les documents"

3. **Références et preuves** :
   - Cite les sources avec leur titre exact pour appuyer tes explications
   - Mentionne les articles, chapitres, titres quand ils sont disponibles
   - Reste factuel et précis

4. **Si l'utilisateur demande un nombre spécifique de sources** :
   - Utilise UNIQUEMENT ce nombre exact parmi les sources ci-dessus (les plus pertinentes)
   - Liste chaque source avec son titre EXACT
   - Fournis un extrait ou résumé pertinent pour chacune

EXEMPLE DE FORMAT PROFESSIONNEL:

Si les sources fournies sont:
SOURCE N°1: Plan Comptable OHADA : Partie 2 - Chapitre 35 (Article 15)
SOURCE N°2: Actes Uniformes : Organisation Des Sûretés - Titre 5 (Article 42)

Et l'utilisateur demande "donne-moi 2 sources sur les contrats", réponds:

Voici 2 sources pertinentes sur les contrats :

**1. Plan Comptable OHADA : Partie 2 - Chapitre 35**
Selon ce document (Article 15), les contrats de franchise sont définis comme...
[Extrait pertinent avec explication]

**2. Actes Uniformes : Organisation Des Sûretés - Titre 5**
D'après l'article 42 de ce texte, les sûretés contractuelles...
[Extrait pertinent avec explication]"""

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

    def _convert_to_source_documents_enriched(self, documents: List[Dict[str, Any]]) -> List[SourceDocument]:
        """
        Convert internal document format to API schema with ENRICHED metadata
        Used for document sourcing mode to provide detailed document information

        Args:
            documents: List of retrieved documents with metadata

        Returns:
            List of SourceDocument with enriched fields (category, section, file_path, etc.)
        """
        sources = []
        for doc in documents:
            metadata = doc.get("metadata", {})

            file_path = metadata.get("file_path", metadata.get("source", ""))
            title = self._generate_title_from_path(file_path, metadata)

            # Extract additional metadata for sourcing
            metadata_summary = {}
            for key in ["acte_uniforme", "livre", "titre", "article"]:
                if metadata.get(key):
                    metadata_summary[key] = metadata[key]

            sources.append(SourceDocument(
                title=title,
                score=doc.get("score", 0.0),
                category=metadata.get("category"),
                section=metadata.get("section"),
                file_path=file_path,
                document_type=metadata.get("category"),  # Alias for category
                metadata_summary=metadata_summary if metadata_summary else None
            ))
        return sources

    async def query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        db_session: Optional[Any] = None,
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
            db_session: Optional database session for context loading
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
                    db_session=db_session,
                    metadata={
                        "use_reranking": use_reranking,
                        "use_fallback": use_fallback
                    }
                )

                # Add timing and extract metadata to root level (for consistency with stream)
                total_time = time.time() - start_time
                result["latency_ms"] = int(total_time * 1000)
                result["model_used"] = result["metadata"].get("model_used", "unknown")
                result["tokens_used"] = result["metadata"].get("tokens_used", 0)

                # Note: intent_type and other metadata are already set by the workflow
                # in result["metadata"], no need to modify them here

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
                "sources": self._convert_to_source_documents_enriched(documents),
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
        db_session: Optional[Any] = None,
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
                    db_session=db_session,
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
                    "sources": self._convert_to_source_documents_enriched(documents),
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
