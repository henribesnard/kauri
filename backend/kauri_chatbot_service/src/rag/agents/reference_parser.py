"""
Legal Reference Parser - Extrait et normalise les références juridiques OHADA
Gère : Actes Uniformes, Articles, Comptes, Jurisprudences, etc.
"""
import re
from typing import Dict, Optional, List
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class LegalReference:
    """Référence juridique parsée et normalisée"""
    reference_type: str  # "article", "compte", "acte_uniforme", "jurisprudence", "chapitre", "titre"
    number: Optional[str]  # "15", "6012", "056/2023"
    source: Optional[str]  # "AU-OHADA", "CCJA", "Plan Comptable"
    full_text: str  # Texte complet original
    normalized: str  # Forme normalisée pour recherche


class LegalReferenceParser:
    """
    Parser de références juridiques OHADA

    Patterns supportés :
    - Articles : "Article 15", "Art. 42", "Art 35 de l'AU-OHADA"
    - Comptes : "Compte 6012", "Compte 601", "Classe 6"
    - Actes Uniformes : "AU-OHADA", "Acte Uniforme relatif au droit commercial"
    - Jurisprudences : "CCJA/2023/056", "Arrêt n°056/2023"
    - Titres/Chapitres : "Titre 3", "Chapitre 5", "Livre 2"
    """

    def __init__(self):
        """Initialize parser with regex patterns"""

        # Pattern pour articles
        self.article_pattern = re.compile(
            r'(?:article|art\.?)\s+(\d+)(?:\s+(?:de|du|de l\'|au)\s+(.+?))?(?:\s|,|\.|\)|$)',
            re.IGNORECASE
        )

        # Pattern pour comptes comptables
        self.compte_pattern = re.compile(
            r'(?:compte|cpt\.?)\s+(\d{1,4})(?:\s|,|\.|\)|$)',
            re.IGNORECASE
        )

        # Pattern pour classe comptable
        self.classe_pattern = re.compile(
            r'classe\s+(\d)(?:\s|,|\.|\)|$)',
            re.IGNORECASE
        )

        # Pattern pour Actes Uniformes
        self.au_pattern = re.compile(
            r'(?:acte\s+uniforme|AU)[\s-]+(?:OHADA|relatif\s+(?:au|à|à\s+l\')\s+(.+?))?(?:\s|,|\.|\)|$)',
            re.IGNORECASE
        )

        # Pattern pour jurisprudences CCJA
        self.ccja_pattern = re.compile(
            r'CCJA[/\s-]+(?:arrêt\s+)?(?:n°|n°\s+)?(\d+)[/\s-]+(\d{4})',
            re.IGNORECASE
        )

        # Pattern pour titres/chapitres/livres
        self.structure_pattern = re.compile(
            r'(?:titre|chapitre|livre|section)\s+(\d+|[IVX]+)(?:\s|,|\.|\)|$)',
            re.IGNORECASE
        )

        # Pattern pour SYSCOHADA
        self.syscohada_pattern = re.compile(
            r'SYSCOHADA(?:\s+révisé)?',
            re.IGNORECASE
        )

    def parse(self, query: str) -> List[LegalReference]:
        """
        Parse une requête et extrait toutes les références juridiques

        Args:
            query: Texte de la requête utilisateur

        Returns:
            Liste de références juridiques détectées
        """
        references = []

        # 1. Chercher articles
        for match in self.article_pattern.finditer(query):
            article_num = match.group(1)
            source = match.group(2) if match.group(2) else None
            full_text = match.group(0).strip()

            references.append(LegalReference(
                reference_type="article",
                number=article_num,
                source=source,
                full_text=full_text,
                normalized=f"Article {article_num}"
            ))

        # 2. Chercher comptes
        for match in self.compte_pattern.finditer(query):
            compte_num = match.group(1)
            full_text = match.group(0).strip()

            references.append(LegalReference(
                reference_type="compte",
                number=compte_num,
                source="Plan Comptable OHADA",
                full_text=full_text,
                normalized=f"Compte {compte_num}"
            ))

        # 3. Chercher classes comptables
        for match in self.classe_pattern.finditer(query):
            classe_num = match.group(1)
            full_text = match.group(0).strip()

            references.append(LegalReference(
                reference_type="classe",
                number=classe_num,
                source="Plan Comptable OHADA",
                full_text=full_text,
                normalized=f"Classe {classe_num}"
            ))

        # 4. Chercher Actes Uniformes
        for match in self.au_pattern.finditer(query):
            subject = match.group(1) if match.group(1) else "OHADA"
            full_text = match.group(0).strip()

            references.append(LegalReference(
                reference_type="acte_uniforme",
                number=None,
                source="AU-OHADA",
                full_text=full_text,
                normalized=f"Acte Uniforme OHADA"
            ))

        # 5. Chercher jurisprudences CCJA
        for match in self.ccja_pattern.finditer(query):
            case_num = match.group(1)
            year = match.group(2)
            full_text = match.group(0).strip()

            references.append(LegalReference(
                reference_type="jurisprudence",
                number=f"{case_num}/{year}",
                source="CCJA",
                full_text=full_text,
                normalized=f"CCJA/{year}/{case_num}"
            ))

        # 6. Chercher structures (Titre, Chapitre, Livre)
        for match in self.structure_pattern.finditer(query):
            struct_type = match.group(0).split()[0].lower()
            struct_num = match.group(1)
            full_text = match.group(0).strip()

            references.append(LegalReference(
                reference_type=struct_type,
                number=struct_num,
                source=None,
                full_text=full_text,
                normalized=f"{struct_type.capitalize()} {struct_num}"
            ))

        # 7. Chercher SYSCOHADA
        for match in self.syscohada_pattern.finditer(query):
            full_text = match.group(0).strip()

            references.append(LegalReference(
                reference_type="syscohada",
                number=None,
                source="SYSCOHADA",
                full_text=full_text,
                normalized="SYSCOHADA"
            ))

        if references:
            logger.info("legal_references_parsed",
                       query=query[:100],
                       num_references=len(references),
                       types=[ref.reference_type for ref in references])

        return references

    def extract_document_type(self, query: str) -> Optional[str]:
        """
        Détermine le type de document principal recherché

        Args:
            query: Texte de la requête

        Returns:
            Type de document : "jurisprudence", "doctrine", "acte_uniforme", "plan_comptable", None
        """
        query_lower = query.lower()

        # Keywords par type de document
        type_keywords = {
            "jurisprudence": [
                "jurisprudence", "arrêt", "ccja", "cour", "décision",
                "jugement", "tribunal", "juridiction"
            ],
            "doctrine": [
                "doctrine", "auteur", "commentaire", "analyse", "étude",
                "article (académique)", "publication", "revue"
            ],
            "acte_uniforme": [
                "acte uniforme", "au-ohada", "au ohada", "traité", "texte législatif"
            ],
            "plan_comptable": [
                "plan comptable", "compte", "classe", "syscohada",
                "comptabilisation", "écriture comptable", "journal"
            ]
        }

        # Compter les matches par type
        type_scores = {}
        for doc_type, keywords in type_keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                type_scores[doc_type] = score

        # Retourner le type avec le plus de matches
        if type_scores:
            best_type = max(type_scores.items(), key=lambda x: x[1])[0]
            logger.info("document_type_detected", query=query[:100], type=best_type)
            return best_type

        return None

    def extract_jurisdiction(self, query: str) -> Optional[str]:
        """
        Extrait la juridiction mentionnée

        Args:
            query: Texte de la requête

        Returns:
            Juridiction : "CCJA", "Cour Suprême", "Cour d'Appel", etc.
        """
        query_lower = query.lower()

        jurisdictions = {
            "ccja": ["ccja", "cour commune"],
            "cour_supreme": ["cour suprême", "cour supreme"],
            "cour_appel": ["cour d'appel", "cour d appel"],
            "tribunal_commerce": ["tribunal de commerce", "tribunal commercial"],
        }

        for jurisdiction, keywords in jurisdictions.items():
            if any(kw in query_lower for kw in keywords):
                logger.info("jurisdiction_detected", query=query[:100], jurisdiction=jurisdiction)
                return jurisdiction

        return None


# Singleton instance
_reference_parser_instance: Optional[LegalReferenceParser] = None


def get_reference_parser() -> LegalReferenceParser:
    """Get singleton reference parser instance"""
    global _reference_parser_instance
    if _reference_parser_instance is None:
        _reference_parser_instance = LegalReferenceParser()
    return _reference_parser_instance
