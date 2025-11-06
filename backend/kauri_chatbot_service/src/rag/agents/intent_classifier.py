"""
Intent Classifier Agent - Détecte l'intention de l'utilisateur
Utilise un LLM pour classifier l'intention et router vers le bon workflow
"""
from typing import Literal, TypedDict
import json
from pydantic import BaseModel, Field
import structlog
from src.config import settings
from src.llm.llm_client import get_llm_client

logger = structlog.get_logger()


class IntentClassification(BaseModel):
    """Classification d'intention structurée"""
    intent_type: Literal["general_conversation", "rag_query", "clarification", "document_sourcing"] = Field(
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


class IntentClassifierAgent:
    """
    Agent de classification d'intention qui détermine si une question
    nécessite une recherche RAG ou peut être répondue directement.
    """

    def __init__(self):
        """Initialize intent classifier with LLM"""
        # Use DeepSeek via LLMClient (same as response agent)
        self.llm_client = get_llm_client()

        # System prompt for classification
        self.system_prompt = """Tu es un agent de classification d'intention pour KAURI, un assistant spécialisé en comptabilité OHADA.

Ton rôle est de classifier l'intention de l'utilisateur en 4 catégories :

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

Règles de classification :
- Questions hors OHADA (politique, sport, météo, etc.) → clarification + recadrage
- Questions vagues sans contexte comptable → clarification + demande précision
- Questions "où trouver", "quels documents", "existe-t-il" → document_sourcing
- Termes comptables/financiers avec demande de définition/explication → rag_query
- Questions sur KAURI lui-même → general_conversation + réponse courte
- Évalue ta confiance objectivement (0.0 = incertain, 1.0 = très certain)

Réponds UNIQUEMENT avec un objet JSON au format suivant (sans markdown, sans backticks) :
{
  "intent_type": "general_conversation" | "rag_query" | "clarification" | "document_sourcing",
  "confidence": 0.95,
  "reasoning": "Explication courte",
  "direct_answer": "Réponse courte et directe" (OBLIGATOIRE si general_conversation ou clarification, JSON avec keywords si document_sourcing, null si rag_query)
}"""

    async def classify_intent(self, query: str) -> tuple[IntentClassification, dict]:
        """
        Classify user intent using LLM

        Args:
            query: User question to classify

        Returns:
            Tuple of (IntentClassification, llm_metadata dict with model_used and tokens_used)
        """
        logger.info("intent_classification_start", query=query[:100])

        try:
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

            logger.info("intent_classification_complete",
                       query=query[:100],
                       intent_type=result.intent_type,
                       confidence=result.confidence,
                       reasoning=result.reasoning,
                       has_direct_answer=bool(result.direct_answer),
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
