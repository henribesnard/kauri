"""
Legal Report Generator - Génère des rapports structurés professionnels
Pour juristes et comptables dans l'espace OHADA
"""
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
import structlog
from pydantic import BaseModel

from src.llm.llm_client import get_llm_client
from src.config import settings

logger = structlog.get_logger()


class ReportSection(BaseModel):
    """Section d'un rapport juridique"""
    title: str
    content: str
    sources: List[Dict[str, Any]] = []
    subsections: List['ReportSection'] = []


class LegalReport(BaseModel):
    """Rapport juridique structuré complet"""
    report_type: Literal["jurisprudence", "doctrine", "reference", "comparative"]
    title: str
    summary: str
    sections: List[ReportSection]
    total_sources: int
    generated_at: str
    metadata: Dict[str, Any] = {}


class LegalReportGenerator:
    """
    Générateur de rapports juridiques structurés

    Types de rapports :
    1. Rapport jurisprudentiel : Analyse de jurisprudences sur un sujet
    2. Rapport doctrinal : Synthèse de doctrines/commentaires
    3. Rapport de référence : Analyse détaillée d'une référence précise
    4. Rapport comparatif : Comparaison de positions juridiques
    """

    def __init__(self):
        """Initialize report generator with LLM client"""
        self.llm_client = get_llm_client()
        logger.info("legal_report_generator_initialized")

    async def generate_jurisprudence_report(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        jurisdiction: Optional[str] = None
    ) -> LegalReport:
        """
        Génère un rapport jurisprudentiel structuré

        Args:
            query: Question de l'utilisateur
            documents: Jurisprudences trouvées
            jurisdiction: Juridiction filtrée (optionnel)

        Returns:
            Rapport structuré avec analyse par décision et synthèse
        """
        logger.info("generating_jurisprudence_report",
                   query=query[:100],
                   num_documents=len(documents),
                   jurisdiction=jurisdiction)

        if not documents:
            return LegalReport(
                report_type="jurisprudence",
                title=f"Recherche jurisprudentielle : {query}",
                summary="Aucune jurisprudence trouvée sur ce sujet.",
                sections=[],
                total_sources=0,
                generated_at=datetime.now().isoformat(),
                metadata={"jurisdiction": jurisdiction}
            )

        # Prepare context for LLM
        context = self._format_documents_for_report(documents)

        # Generate structured analysis
        system_prompt = """Tu es un assistant juridique spécialisé en droit OHADA.
Tu génères des rapports jurisprudentiels structurés et professionnels.

Ton rapport doit suivre cette structure :

## 1. Résumé Exécutif
[Synthèse en 2-3 phrases des principales jurisprudences et tendances]

## 2. Analyse par Décision

Pour chaque jurisprudence importante (maximum 5) :

### [Titre exact de la décision]
**Référence :** [Juridiction, date, numéro]
**Faits :** [Résumé des faits pertinents]
**Principe juridique :** [Règle de droit dégagée]
**Motivation :** [Extrait pertinent de la décision]
**Portée :** [Impact et application pratique]

## 3. Synthèse et Tendances
- Cohérence jurisprudentielle
- Évolution dans le temps
- Principes consolidés

## 4. Recommandations Pratiques
[Conseils concrets pour l'application]

IMPORTANT :
- Utilise les titres EXACTS des sources (pas de [Document X])
- Cite les extraits textuellement
- Reste factuel et objectif
- Structure avec markdown (##, ###, **, -, etc.)
"""

        user_prompt = f"""SOURCES JURIDIQUES :
{context}

QUESTION :
{query}

CONTEXTE :
- Juridiction : {jurisdiction or "Toutes juridictions"}
- Nombre de décisions : {len(documents)}

Génère un rapport jurisprudentiel structuré selon le format demandé."""

        llm_response = await self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,  # Factuel et précis
            max_tokens=3000
        )

        report_content = llm_response["content"]

        # Parse sections (simplified for now)
        sections = self._parse_report_sections(report_content)

        report = LegalReport(
            report_type="jurisprudence",
            title=f"Rapport Jurisprudentiel : {query[:80]}",
            summary=self._extract_summary(report_content),
            sections=sections,
            total_sources=len(documents),
            generated_at=datetime.now().isoformat(),
            metadata={
                "jurisdiction": jurisdiction,
                "query": query,
                "model_used": llm_response["model"],
                "tokens_used": llm_response["tokens_used"]
            }
        )

        logger.info("jurisprudence_report_generated",
                   num_sections=len(sections),
                   total_sources=len(documents))

        return report

    async def generate_reference_report(
        self,
        query: str,
        reference: str,
        documents: List[Dict[str, Any]]
    ) -> LegalReport:
        """
        Génère un rapport sur une référence juridique précise

        Args:
            query: Question de l'utilisateur
            reference: Référence ciblée (Article X, Compte Y, etc.)
            documents: Documents trouvés

        Returns:
            Rapport détaillé sur la référence
        """
        logger.info("generating_reference_report",
                   query=query[:100],
                   reference=reference,
                   num_documents=len(documents))

        if not documents:
            return LegalReport(
                report_type="reference",
                title=f"Analyse de référence : {reference}",
                summary=f"Référence {reference} non trouvée dans la base.",
                sections=[],
                total_sources=0,
                generated_at=datetime.now().isoformat(),
                metadata={"reference": reference}
            )

        context = self._format_documents_for_report(documents)

        system_prompt = """Tu es un assistant juridique spécialisé en droit OHADA.
Tu génères des rapports d'analyse de références juridiques (articles, comptes, etc.).

Structure du rapport :

## 1. Identification
- Référence exacte
- Source (Acte Uniforme, Plan Comptable, etc.)
- Chapitre/Titre/Section

## 2. Contenu Intégral
[Texte complet de la référence avec numérotation si applicable]

## 3. Analyse et Commentaires
- Objet et finalité
- Termes clés et définitions
- Champ d'application

## 4. Articulation avec Autres Dispositions
- Références croisées
- Liens avec d'autres articles/comptes
- Cohérence systémique

## 5. Application Pratique
- Exemples concrets
- Cas d'usage
- Points d'attention

## 6. Évolutions et Modifications
[Si applicable : historique des modifications]

IMPORTANT :
- Cite le texte exact de la référence
- Utilise les titres exacts des sources
- Reste précis et factuel
"""

        user_prompt = f"""SOURCES JURIDIQUES :
{context}

RÉFÉRENCE RECHERCHÉE :
{reference}

QUESTION :
{query}

Génère un rapport d'analyse détaillé de cette référence."""

        llm_response = await self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,  # Très factuel
            max_tokens=3000
        )

        report_content = llm_response["content"]
        sections = self._parse_report_sections(report_content)

        report = LegalReport(
            report_type="reference",
            title=f"Analyse de Référence : {reference}",
            summary=self._extract_summary(report_content),
            sections=sections,
            total_sources=len(documents),
            generated_at=datetime.now().isoformat(),
            metadata={
                "reference": reference,
                "query": query,
                "model_used": llm_response["model"],
                "tokens_used": llm_response["tokens_used"]
            }
        )

        logger.info("reference_report_generated",
                   reference=reference,
                   num_sections=len(sections))

        return report

    async def generate_comparative_report(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        comparison_criteria: Optional[List[str]] = None
    ) -> LegalReport:
        """
        Génère un rapport comparatif (ex: différentes positions doctrinales)

        Args:
            query: Question de l'utilisateur
            documents: Documents à comparer
            comparison_criteria: Critères de comparaison (optionnel)

        Returns:
            Rapport comparatif structuré
        """
        logger.info("generating_comparative_report",
                   query=query[:100],
                   num_documents=len(documents))

        context = self._format_documents_for_report(documents)

        system_prompt = """Tu es un assistant juridique spécialisé en droit OHADA.
Tu génères des rapports comparatifs analysant différentes positions juridiques.

Structure du rapport :

## 1. Synthèse Comparative
[Tableau récapitulatif des positions principales]

## 2. Analyse par Source

### [Source 1]
- Position défendue
- Arguments principaux
- Fondements juridiques

### [Source 2]
[...]

## 3. Points de Convergence
- Consensus identifiés
- Principes partagés

## 4. Points de Divergence
- Désaccords majeurs
- Nuances d'interprétation
- Débats ouverts

## 5. Analyse Critique
- Forces et faiblesses de chaque position
- Tendance majoritaire (si applicable)

## 6. Implications Pratiques
- Recommandations selon les positions
- Risques juridiques à considérer

IMPORTANT :
- Objectivité et neutralité
- Citations exactes
- Titres exacts des sources
"""

        user_prompt = f"""SOURCES À COMPARER :
{context}

QUESTION :
{query}

CRITÈRES DE COMPARAISON :
{', '.join(comparison_criteria) if comparison_criteria else 'Analyse générale'}

Génère un rapport comparatif structuré."""

        llm_response = await self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=3500
        )

        report_content = llm_response["content"]
        sections = self._parse_report_sections(report_content)

        report = LegalReport(
            report_type="comparative",
            title=f"Analyse Comparative : {query[:80]}",
            summary=self._extract_summary(report_content),
            sections=sections,
            total_sources=len(documents),
            generated_at=datetime.now().isoformat(),
            metadata={
                "query": query,
                "comparison_criteria": comparison_criteria,
                "model_used": llm_response["model"],
                "tokens_used": llm_response["tokens_used"]
            }
        )

        logger.info("comparative_report_generated",
                   num_sections=len(sections))

        return report

    def _format_documents_for_report(self, documents: List[Dict[str, Any]]) -> str:
        """Format documents for report generation"""
        formatted = []

        for i, doc in enumerate(documents, 1):
            metadata = doc.get("metadata", {})
            content = doc.get("content", "")

            # Build title from metadata
            title_parts = []
            if metadata.get("category"):
                title_parts.append(metadata["category"].replace("_", " ").title())
            if metadata.get("title"):
                title_parts.append(metadata["title"])
            if metadata.get("file_path"):
                filename = metadata["file_path"].split("/")[-1].replace(".pdf", "")
                if filename not in str(title_parts):
                    title_parts.append(filename)

            title = " - ".join(title_parts) if title_parts else f"Document {i}"

            formatted.append(f"\n### SOURCE {i}: {title}")
            formatted.append(f"**Score:** {doc.get('score', 0):.3f}")

            # Add key metadata
            if metadata.get("date"):
                formatted.append(f"**Date:** {metadata['date']}")
            if metadata.get("jurisdiction"):
                formatted.append(f"**Juridiction:** {metadata['jurisdiction']}")
            if metadata.get("case_number"):
                formatted.append(f"**Référence:** {metadata['case_number']}")

            formatted.append(f"\n**Contenu:**\n{content}\n")
            formatted.append("-" * 80)

        return "\n".join(formatted)

    def _parse_report_sections(self, content: str) -> List[ReportSection]:
        """Parse markdown content into sections (simplified)"""
        sections = []
        lines = content.split("\n")

        current_section = None
        current_content = []

        for line in lines:
            if line.startswith("## "):
                # New section
                if current_section:
                    current_section.content = "\n".join(current_content).strip()
                    sections.append(current_section)

                title = line.replace("## ", "").strip()
                current_section = ReportSection(title=title, content="")
                current_content = []
            elif current_section:
                current_content.append(line)

        # Add last section
        if current_section:
            current_section.content = "\n".join(current_content).strip()
            sections.append(current_section)

        return sections

    def _extract_summary(self, content: str) -> str:
        """Extract summary from report (first paragraph or dedicated section)"""
        lines = content.split("\n")

        # Look for "Résumé" section
        in_summary = False
        summary_lines = []

        for line in lines:
            if "résumé" in line.lower() and line.startswith("#"):
                in_summary = True
                continue
            if in_summary:
                if line.startswith("#"):
                    break
                if line.strip():
                    summary_lines.append(line.strip())

        if summary_lines:
            return " ".join(summary_lines)[:300]

        # Fallback: first non-empty paragraph
        for line in lines:
            if line.strip() and not line.startswith("#"):
                return line.strip()[:300]

        return "Rapport généré avec succès."

    def format_report_as_text(self, report: LegalReport) -> str:
        """Format report as plain text for API response"""
        output = []

        # Header
        output.append("=" * 80)
        output.append(report.title.upper())
        output.append("=" * 80)
        output.append(f"Généré le : {report.generated_at}")
        output.append(f"Type : {report.report_type.title()}")
        output.append(f"Sources : {report.total_sources}")
        output.append("")

        # Summary
        output.append("RÉSUMÉ")
        output.append("-" * 80)
        output.append(report.summary)
        output.append("")

        # Sections
        for section in report.sections:
            output.append("")
            output.append(section.title.upper())
            output.append("-" * 80)
            output.append(section.content)

        output.append("")
        output.append("=" * 80)
        output.append("Fin du rapport")
        output.append("=" * 80)

        return "\n".join(output)


# Singleton instance
_report_generator_instance: Optional[LegalReportGenerator] = None


def get_report_generator() -> LegalReportGenerator:
    """Get singleton report generator instance"""
    global _report_generator_instance
    if _report_generator_instance is None:
        _report_generator_instance = LegalReportGenerator()
    return _report_generator_instance
