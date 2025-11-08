"""
Legal Retriever - Retriever spécialisé pour recherches juridiques OHADA
Étend HybridRetriever avec filtrage par métadonnées juridiques
"""
from typing import List, Dict, Any, Optional
import structlog

from ...config import settings
from .hybrid_retriever import get_hybrid_retriever
from ..agents.reference_parser import get_reference_parser, LegalReference

logger = structlog.get_logger()


class LegalRetriever:
    """
    Retriever spécialisé pour recherches juridiques

    Fonctionnalités :
    - Recherche par référence exacte (Article X, Compte Y)
    - Filtrage par type de document (jurisprudence, doctrine, AU, plan comptable)
    - Filtrage par juridiction (CCJA, Cour Suprême, etc.)
    - Recherche de proximité (documents liés)
    """

    def __init__(self):
        """Initialize legal retriever with hybrid retriever and reference parser"""
        self.hybrid_retriever = get_hybrid_retriever()
        self.reference_parser = get_reference_parser()

        logger.info("legal_retriever_initialized")

    async def retrieve_by_reference(
        self,
        reference: LegalReference,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recherche par référence juridique exacte

        Args:
            reference: Référence parsée (Article, Compte, etc.)
            top_k: Nombre de résultats

        Returns:
            Documents correspondant à la référence
        """
        logger.info("legal_retrieve_by_reference",
                   ref_type=reference.reference_type,
                   ref_number=reference.number,
                   ref_source=reference.source)

        # Build query from reference
        query = reference.normalized
        if reference.source:
            query += f" {reference.source}"

        # Retrieve with hybrid search
        documents = await self.hybrid_retriever.retrieve(
            query=query,
            top_k=top_k * 2,  # Get more candidates
            use_reranking=True
        )

        # Filter by reference metadata if available
        filtered_docs = []
        for doc in documents:
            metadata = doc.get("metadata", {})

            # Match by reference type
            if reference.reference_type == "article":
                if metadata.get("article") == reference.number:
                    filtered_docs.append(doc)
            elif reference.reference_type == "compte" or reference.reference_type == "classe":
                if metadata.get("compte") == reference.number or metadata.get("classe") == reference.number:
                    filtered_docs.append(doc)
            elif reference.reference_type == "jurisprudence":
                if metadata.get("case_number") == reference.number:
                    filtered_docs.append(doc)
            elif reference.reference_type in ["titre", "chapitre", "livre"]:
                # Check in metadata or content
                if (metadata.get(reference.reference_type) == reference.number or
                    reference.normalized.lower() in doc.get("content", "").lower()[:200]):
                    filtered_docs.append(doc)
            else:
                # Fallback: keep all results (rely on reranking)
                filtered_docs.append(doc)

        # If filtering gave results, use them; otherwise return all
        result_docs = filtered_docs[:top_k] if filtered_docs else documents[:top_k]

        logger.info("legal_retrieve_by_reference_complete",
                   total_results=len(documents),
                   filtered_results=len(filtered_docs),
                   final_results=len(result_docs))

        return result_docs

    async def retrieve_by_document_type(
        self,
        query: str,
        document_type: str,
        jurisdiction: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recherche filtrée par type de document juridique

        Args:
            query: Texte de recherche
            document_type: Type de document (jurisprudence, doctrine, acte_uniforme, plan_comptable)
            jurisdiction: Juridiction optionnelle (CCJA, etc.)
            top_k: Nombre de résultats

        Returns:
            Documents filtrés par type
        """
        logger.info("legal_retrieve_by_document_type",
                   query=query[:100],
                   document_type=document_type,
                   jurisdiction=jurisdiction)

        # Retrieve with hybrid search (larger set)
        documents = await self.hybrid_retriever.retrieve(
            query=query,
            top_k=top_k * 3,  # Get more candidates for filtering
            use_reranking=True
        )

        # Filter by document type
        filtered_docs = []
        for doc in documents:
            metadata = doc.get("metadata", {})
            category = metadata.get("category", "").lower()

            # Match category
            type_match = False
            if document_type == "jurisprudence" and "jurisprudence" in category:
                type_match = True
            elif document_type == "doctrine" and "doctrine" in category:
                type_match = True
            elif document_type == "acte_uniforme" and ("acte" in category or "uniforme" in category):
                type_match = True
            elif document_type == "plan_comptable" and ("plan" in category or "comptable" in category):
                type_match = True

            if not type_match:
                continue

            # Filter by jurisdiction if specified
            if jurisdiction:
                doc_jurisdiction = metadata.get("jurisdiction", "").lower()
                if jurisdiction.lower() not in doc_jurisdiction:
                    continue

            filtered_docs.append(doc)

        result_docs = filtered_docs[:top_k]

        logger.info("legal_retrieve_by_document_type_complete",
                   total_results=len(documents),
                   filtered_results=len(filtered_docs),
                   final_results=len(result_docs))

        return result_docs

    async def retrieve_case_law(
        self,
        topic: str,
        jurisdiction: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recherche spécialisée de jurisprudences

        Args:
            topic: Sujet de recherche
            jurisdiction: Juridiction optionnelle (CCJA, Cour Suprême, etc.)
            top_k: Nombre de résultats

        Returns:
            Jurisprudences pertinentes
        """
        logger.info("legal_retrieve_case_law",
                   topic=topic[:100],
                   jurisdiction=jurisdiction)

        # Use document_type filter for jurisprudence
        return await self.retrieve_by_document_type(
            query=topic,
            document_type="jurisprudence",
            jurisdiction=jurisdiction,
            top_k=top_k
        )

    async def retrieve_related(
        self,
        reference_doc: Dict[str, Any],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recherche de documents liés à un document de référence

        Args:
            reference_doc: Document de référence
            top_k: Nombre de documents liés

        Returns:
            Documents similaires/liés
        """
        logger.info("legal_retrieve_related",
                   ref_doc_id=reference_doc.get("id", "unknown"))

        # Extract key concepts from reference document
        content = reference_doc.get("content", "")
        metadata = reference_doc.get("metadata", {})

        # Build query from key metadata
        query_parts = []
        if metadata.get("category"):
            query_parts.append(metadata["category"])
        if metadata.get("legal_topics"):
            query_parts.extend(metadata["legal_topics"])

        # Use content excerpt if metadata is sparse
        if len(query_parts) < 2:
            query_parts.append(content[:200])

        query = " ".join(query_parts)

        # Retrieve similar documents
        documents = await self.hybrid_retriever.retrieve(
            query=query,
            top_k=top_k + 1,  # +1 to exclude original
            use_reranking=True
        )

        # Filter out the reference document itself
        related_docs = [
            doc for doc in documents
            if doc.get("id") != reference_doc.get("id")
        ][:top_k]

        logger.info("legal_retrieve_related_complete",
                   related_count=len(related_docs))

        return related_docs

    async def retrieve_enhanced(
        self,
        query: str,
        legal_metadata: Optional[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recherche enrichie avec métadonnées juridiques

        Méthode unifiée qui route vers le bon type de recherche selon les métadonnées

        Args:
            query: Texte de recherche
            legal_metadata: Métadonnées juridiques extraites de l'intention
            top_k: Nombre de résultats

        Returns:
            Documents pertinents
        """
        if not legal_metadata:
            # Fallback to standard hybrid retrieval
            logger.info("legal_retrieve_enhanced_fallback_to_hybrid")
            return await self.hybrid_retriever.retrieve(query=query, top_k=top_k)

        # Extract metadata
        document_type = legal_metadata.get("document_type")
        legal_refs = legal_metadata.get("legal_references", [])
        jurisdiction = legal_metadata.get("jurisdiction")
        search_scope = legal_metadata.get("search_scope", "broad")

        logger.info("legal_retrieve_enhanced",
                   query=query[:100],
                   document_type=document_type,
                   num_refs=len(legal_refs) if legal_refs else 0,
                   jurisdiction=jurisdiction,
                   search_scope=search_scope)

        # Route to appropriate retrieval method
        if legal_refs and search_scope == "exact":
            # Recherche par référence précise
            ref_text = legal_refs[0]  # Use first reference
            parsed_refs = self.reference_parser.parse(ref_text)
            if parsed_refs:
                return await self.retrieve_by_reference(
                    reference=parsed_refs[0],
                    top_k=top_k
                )

        if document_type:
            # Recherche filtrée par type de document
            return await self.retrieve_by_document_type(
                query=query,
                document_type=document_type,
                jurisdiction=jurisdiction,
                top_k=top_k
            )

        # Fallback to hybrid retrieval
        logger.info("legal_retrieve_enhanced_fallback")
        return await self.hybrid_retriever.retrieve(query=query, top_k=top_k)


# Singleton instance
_legal_retriever_instance: Optional[LegalRetriever] = None


def get_legal_retriever() -> LegalRetriever:
    """Get singleton legal retriever instance"""
    global _legal_retriever_instance
    if _legal_retriever_instance is None:
        _legal_retriever_instance = LegalRetriever()
    return _legal_retriever_instance
