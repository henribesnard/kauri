"""
Intent Classifier Agent - Détecte l'intention de l'utilisateur
Utilise un LLM pour classifier l'intention et router vers le bon workflow
Version enrichie avec classification juridique avancée
"""
from typing import Literal, TypedDict, Optional
import json
from pydantic import BaseModel, Field
import structlog
from src.config import settings
from src.llm.llm_client import get_llm_client

logger = structlog.get_logger()


class LegalMetadata(BaseModel):
    """Métadonnées juridiques extraites de la requête"""
    document_type: Optional[Literal["jurisprudence", "doctrine", "acte_uniforme", "plan_comptable"]] = Field(
        default=None,
        description="Type de document juridique recherché"
    )
    legal_references: Optional[list[str]] = Field(
        default=None,
        description="Références juridiques mentionnées (Article X, Compte Y, etc.)"
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Juridiction mentionnée (CCJA, Cour Suprême, etc.)"
    )
    search_scope: Optional[Literal["exact", "broad", "related"]] = Field(
        default="broad",
        description="Portée de la recherche souhaitée"
    )


class IntentClassification(BaseModel):
    """Classification d'intention structurée avec métadonnées juridiques"""
    intent_type: Literal[
        "general_conversation",
        "rag_query",
        "clarification",
        "document_sourcing",
        "legal_reference_search",  # NOUVEAU : Recherche par référence précise
        "case_law_research"         # NOUVEAU : Recherche jurisprudentielle approfondie
    ] = Field(
        description="Type d'intention détecté"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Niveau de confiance de la classification (0-1)"
    )
    reasoning: str = Field(
        description="Explication courte du raisonnement"
    )
    direct_answer: str | dict | None = Field(
        default=None,
        description="Réponse directe (string pour general_conversation/clarification, dict pour document_sourcing, null pour rag_query)"
    )
    legal_metadata: Optional[LegalMetadata] = Field(
        default=None,
        description="Métadonnées juridiques extraites (optionnel)"
    )


class IntentClassifierAgent:
    """
    Agent de classification d'intention qui détermine si une question
    nécessite une recherche RAG ou peut être répondue directement.
    """

    def __init__(self):
        """Initialize intent classifier with LLM"""
        # Use DeepSeek via LLMClient (same as response agent)
        self.llm_client = get_llm_client()

        # Import reference parser for enhanced classification
        from .reference_parser import get_reference_parser
        self.reference_parser = get_reference_parser()

        # System prompt for classification (enriched with legal intents)
        self.system_prompt = """Tu es un agent de classification d'intention pour KAURI, un assistant spécialisé en comptabilité OHADA.

Ton rôle est de classifier l'intention de l'utilisateur en 6 catégories :

1. **general_conversation** : Questions générales sur KAURI, salutations, remerciements
   - Exemples : "Bonjour", "Qui es-tu ?", "Merci", "Quel est ton rôle ?", "Que peux-tu faire ?"
   - Ne nécessite PAS de recherche dans la documentation OHADA
   - Tu DOIS générer une réponse directe dans "direct_answer"

   IMPORTANT pour general_conversation :
   - Présente KAURI comme assistant spécialisé en comptabilité OHADA uniquement
   - RECADRE poliment si la question sort du domaine OHADA (politique, sport, météo, etc.)
   - Exemple de recadrage : "Je suis spécialisé en comptabilité OHADA. Pour t'aider efficacement, pose-moi des questions sur le SYSCOHADA, les Actes Uniformes, ou les traitements comptables."

2. **rag_query** : Questions techniques nécessitant la documentation OHADA
   - Exemples : "C'est quoi un amortissement ?", "Comment comptabiliser une créance ?", "Article 15 du SYSCOHADA"
   - Nécessite une recherche RAG dans la base de connaissances
   - Ne génère PAS de "direct_answer"

3. **clarification** : Question ambiguë ou hors-sujet nécessitant recadrage/précisions
   - Exemples : "Qu'est-ce que c'est ?", "Peux-tu m'expliquer ?", "Parle-moi du football"
   - Questions hors domaine OHADA (actualité, divertissement, conseils personnels, etc.)
   - Tu DOIS générer une réponse de recadrage dans "direct_answer"
   - Exemple : "Ma spécialité est la comptabilité OHADA. Peux-tu préciser ta question comptable ? Je peux t'aider sur les écritures, les comptes, les états financiers, etc."

4. **document_sourcing** : Demandes de recherche ou listage de documents (NOUVEAU)
   - Exemples :
     * "Dans quels documents parle-t-on des amortissements ?"
     * "Existe-t-il une jurisprudence sur la comptabilité des stocks ?"
     * "Quels documents traitent de [sujet] ?"
     * "Liste-moi les actes uniformes sur le droit commercial"
     * "Où puis-je trouver des infos sur [concept comptable] ?"
   - L'utilisateur cherche à connaître LES SOURCES plutôt qu'une réponse directe au concept
   - Tu DOIS extraire les mots-clés et catégorie dans "direct_answer" au format JSON :
     {"keywords": ["mot1", "mot2"], "category_filter": null}
   - category_filter peut être : "doctrine", "jurisprudence", "acte_uniforme", "plan_comptable" ou null

   IMPORTANT : NE PAS classifier comme document_sourcing si l'utilisateur demande une RÉPONSE avec un nombre spécifique de sources :
   - "Donne-moi 3 sources sur X" → rag_query (pas document_sourcing)
   - "Explique avec 5 documents X" → rag_query (pas document_sourcing)
   - "Peux-tu répondre avec 2 sources" → rag_query (pas document_sourcing)
   Ces questions demandent une RÉPONSE utilisant des sources, pas juste un listing de documents.

5. **legal_reference_search** : Recherche par référence juridique précise (NOUVEAU)
   - Exemples :
     * "Que dit l'Article 15 de l'AU-OHADA ?"
     * "Explique-moi le Compte 6012"
     * "Contenu du Chapitre 3 du SYSCOHADA"
     * "CCJA/2023/056"
   - L'utilisateur cite une référence PRÉCISE (Article X, Compte Y, Arrêt Z)
   - Nécessite une recherche ciblée sur cette référence exacte
   - Ne génère PAS de "direct_answer", mais EXTRAIT les métadonnées dans "legal_metadata" :
     {
       "document_type": "acte_uniforme" | "plan_comptable" | "jurisprudence" | null,
       "legal_references": ["Article 15", "Compte 6012"],
       "jurisdiction": "CCJA" (si applicable),
       "search_scope": "exact"
     }

6. **case_law_research** : Recherche jurisprudentielle approfondie (NOUVEAU)
   - Exemples :
     * "Jurisprudence de la CCJA sur les amortissements"
     * "Décisions de justice concernant les stocks"
     * "Arrêts sur la comptabilisation des provisions"
   - L'utilisateur cherche des décisions de justice sans référence précise
   - Nécessite recherche large dans les jurisprudences
   - Extrait métadonnées dans "legal_metadata" :
     {
       "document_type": "jurisprudence",
       "legal_references": null,
       "jurisdiction": "CCJA" (si mentionnée),
       "search_scope": "broad"
     }

Règles de classification :
- Questions hors OHADA (politique, sport, météo, etc.) → clarification + recadrage
- Questions vagues sans contexte comptable → clarification + demande précision
- Questions "où trouver", "quels documents", "existe-t-il" → document_sourcing
- Référence juridique précise citée (Article X, Compte Y) → legal_reference_search
- Demande de jurisprudence sans référence précise → case_law_research
- Termes comptables/financiers avec demande de définition/explication → rag_query
- Questions sur KAURI lui-même → general_conversation + réponse courte
- Évalue ta confiance objectivement (0.0 = incertain, 1.0 = très certain)

Réponds UNIQUEMENT avec un objet JSON au format suivant (sans markdown, sans backticks) :
{
  "intent_type": "general_conversation" | "rag_query" | "clarification" | "document_sourcing" | "legal_reference_search" | "case_law_research",
  "confidence": 0.95,
  "reasoning": "Explication courte",
  "direct_answer": "Réponse courte et directe" (OBLIGATOIRE si general_conversation ou clarification, JSON avec keywords si document_sourcing, null pour autres),
  "legal_metadata": {
    "document_type": "jurisprudence" | "doctrine" | "acte_uniforme" | "plan_comptable" | null,
    "legal_references": ["Article 15"] (si applicable),
    "jurisdiction": "CCJA" (si applicable),
    "search_scope": "exact" | "broad" | "related"
  } (OPTIONNEL, uniquement si legal_reference_search ou case_law_research)
}"""

    async def classify_intent(self, query: str) -> tuple[IntentClassification, dict]:
        """
        Classify user intent using LLM with enhanced legal reference parsing

        Args:
            query: User question to classify

        Returns:
            Tuple of (IntentClassification, llm_metadata dict with model_used and tokens_used)
        """
        logger.info("intent_classification_start", query=query[:100])

        try:
            # Pre-parse legal references to help LLM classification
            legal_refs = self.reference_parser.parse(query)
            doc_type = self.reference_parser.extract_document_type(query)
            jurisdiction = self.reference_parser.extract_jurisdiction(query)

            if legal_refs:
                logger.info("pre_parsed_legal_references",
                           query=query[:100],
                           num_refs=len(legal_refs),
                           types=[ref.reference_type for ref in legal_refs])

            # Call LLM with configured parameters
            llm_response = await self.llm_client.generate(
                prompt=query,
                system_prompt=self.system_prompt,
                temperature=settings.intent_classifier_temperature,
                max_tokens=settings.intent_classifier_max_tokens,
                use_fallback=False  # Use primary (DeepSeek) for fast classification
            )

            # Parse JSON response
            content = llm_response["content"].strip()

            # Remove markdown code blocks if present
            if content.startswith("```"):
                # Extract JSON from markdown code block
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()

            # Parse JSON
            parsed = json.loads(content)
            result = IntentClassification(**parsed)

            # Enrich with parsed legal metadata if not provided by LLM
            if result.intent_type in ["legal_reference_search", "case_law_research"]:
                if not result.legal_metadata and (legal_refs or doc_type or jurisdiction):
                    result.legal_metadata = LegalMetadata(
                        document_type=doc_type,
                        legal_references=[ref.normalized for ref in legal_refs] if legal_refs else None,
                        jurisdiction=jurisdiction,
                        search_scope="exact" if legal_refs else "broad"
                    )
                    logger.info("legal_metadata_enriched_from_parser",
                               doc_type=doc_type,
                               num_refs=len(legal_refs) if legal_refs else 0)

            logger.info("intent_classification_complete",
                       query=query[:100],
                       intent_type=result.intent_type,
                       confidence=result.confidence,
                       reasoning=result.reasoning,
                       has_direct_answer=bool(result.direct_answer),
                       has_legal_metadata=bool(result.legal_metadata),
                       model_used=llm_response["model"])

            # Return result + LLM metadata
            llm_metadata = {
                "model_used": llm_response["model"],
                "tokens_used": llm_response["tokens_used"]
            }
            return result, llm_metadata

        except json.JSONDecodeError as e:
            logger.error("intent_classification_json_error",
                        error=str(e),
                        query=query[:100],
                        content=llm_response.get("content", "")[:200])
            # Fallback conservateur : assumer rag_query en cas d'erreur de parsing
            return IntentClassification(
                intent_type="rag_query",
                confidence=0.5,
                reasoning=f"JSON parsing failed, defaulting to rag_query",
                direct_answer=None
            ), {"model_used": "unknown", "tokens_used": 0}
        except Exception as e:
            logger.error("intent_classification_error", error=str(e), query=query[:100])
            # Fallback conservateur : assumer rag_query en cas d'erreur
            return IntentClassification(
                intent_type="rag_query",
                confidence=0.5,
                reasoning=f"Classification failed, defaulting to rag_query: {str(e)}",
                direct_answer=None
            ), {"model_used": "unknown", "tokens_used": 0}


# Singleton instance
_intent_classifier_instance: IntentClassifierAgent | None = None


def get_intent_classifier() -> IntentClassifierAgent:
    """Get singleton intent classifier instance"""
    global _intent_classifier_instance
    if _intent_classifier_instance is None:
        _intent_classifier_instance = IntentClassifierAgent()
    return _intent_classifier_instance
