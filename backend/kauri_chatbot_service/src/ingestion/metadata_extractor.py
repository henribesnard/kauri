"""
Legal Metadata Extractor - Extrait automatiquement les métadonnées juridiques
lors de l'ingestion des documents OHADA
"""
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
import structlog

logger = structlog.get_logger()


class LegalMetadataExtractor:
    """
    Extracteur de métadonnées juridiques pour documents OHADA

    Extrait automatiquement :
    - Type de document (jurisprudence, doctrine, acte_uniforme, plan_comptable)
    - Références juridiques (articles, comptes, titres)
    - Juridiction (pour jurisprudences)
    - Date de publication/décision
    - Numéros de référence (arrêts, cas)
    - Thématiques juridiques
    """

    def __init__(self):
        """Initialize metadata extractor with patterns"""

        # Patterns pour identification du type de document
        self.type_patterns = {
            "jurisprudence": [
                r"(?i)ccja",
                r"(?i)cour\s+(?:suprême|d'appel|commune)",
                r"(?i)arrêt\s+n°",
                r"(?i)jugement",
                r"(?i)décision\s+n°"
            ],
            "acte_uniforme": [
                r"(?i)acte\s+uniforme",
                r"(?i)au[-\s]ohada",
                r"(?i)traité\s+ohada"
            ],
            "plan_comptable": [
                r"(?i)plan\s+comptable",
                r"(?i)syscohada",
                r"(?i)compte\s+\d{2,4}",
                r"(?i)classe\s+[1-9]"
            ],
            "doctrine": [
                r"(?i)commentaire",
                r"(?i)analyse",
                r"(?i)doctrine",
                r"(?i)étude"
            ]
        }

        # Pattern pour extraire articles
        self.article_pattern = re.compile(
            r'(?i)(?:article|art\.?)\s+(\d+(?:\s*[-–]\s*\d+)?)',
            re.MULTILINE
        )

        # Pattern pour extraire comptes
        self.compte_pattern = re.compile(
            r'(?i)compte\s+(\d{2,4})',
            re.MULTILINE
        )

        # Pattern pour extraire classe comptable
        self.classe_pattern = re.compile(
            r'(?i)classe\s+([1-9])',
            re.MULTILINE
        )

        # Pattern pour juridiction
        self.jurisdiction_patterns = {
            "CCJA": re.compile(r'(?i)ccja|cour\s+commune'),
            "Cour Suprême": re.compile(r'(?i)cour\s+supr[eê]me'),
            "Cour d'Appel": re.compile(r"(?i)cour\s+d'appel"),
            "Tribunal de Commerce": re.compile(r'(?i)tribunal\s+(?:de\s+)?commerce')
        }

        # Pattern pour numéro d'arrêt
        self.case_number_pattern = re.compile(
            r'(?i)(?:arrêt|décision|jugement)\s+(?:n°|numéro|no\.?)\s*(\d+[/\-]\d{2,4})',
            re.MULTILINE
        )

        # Pattern pour date
        self.date_pattern = re.compile(
            r'(\d{1,2})\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})',
            re.IGNORECASE
        )

        # Thématiques juridiques courantes
        self.legal_topics_keywords = {
            "amortissement": ["amortissement", "dépréciation", "durée d'utilité"],
            "immobilisation": ["immobilisation", "actif immobilisé", "immobilisation corporelle"],
            "provision": ["provision", "charge probable", "passif éventuel"],
            "stock": ["stock", "inventaire", "marchandise"],
            "créance": ["créance", "débiteur", "recouvrement"],
            "dette": ["dette", "créancier", "passif exigible"],
            "capital": ["capital", "capital social", "apport"],
            "résultat": ["résultat", "bénéfice", "perte"],
            "consolidation": ["consolidation", "comptes consolidés", "groupe"],
            "comptabilité générale": ["comptabilité générale", "plan comptable", "nomenclature"],
        }

        logger.info("legal_metadata_extractor_initialized")

    def extract_metadata(
        self,
        file_path: str,
        content: str,
        existing_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extrait les métadonnées juridiques d'un document

        Args:
            file_path: Chemin du fichier source
            content: Contenu textuel du document
            existing_metadata: Métadonnées existantes à enrichir

        Returns:
            Dictionnaire de métadonnées enrichies
        """
        metadata = existing_metadata.copy() if existing_metadata else {}

        # Extract from file path
        path_metadata = self._extract_from_path(file_path)
        metadata.update(path_metadata)

        # Extract from content
        content_metadata = self._extract_from_content(content, file_path)
        metadata.update(content_metadata)

        # Ensure file_path is stored
        metadata["file_path"] = file_path

        logger.info("metadata_extracted",
                   file_path=file_path[:60],
                   category=metadata.get("category"),
                   num_articles=len(metadata.get("articles_references", [])),
                   num_topics=len(metadata.get("legal_topics", [])))

        return metadata

    def _extract_from_path(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from file path structure"""
        metadata = {}
        path = Path(file_path)

        # Normalize path
        path_str = str(path).replace("\\", "/").lower()

        # Detect category from path
        if "jurisprudence" in path_str:
            metadata["category"] = "jurisprudence"
        elif "actes_uniformes" in path_str or "acte_uniforme" in path_str:
            metadata["category"] = "acte_uniforme"
        elif "plan_comptable" in path_str:
            metadata["category"] = "plan_comptable"
        elif "doctrine" in path_str:
            metadata["category"] = "doctrine"
        elif "presentation" in path_str:
            metadata["category"] = "presentation"

        # Extract section from path (e.g., "droit_commercial", "partie_2")
        parts = path_str.split("/")
        if len(parts) >= 2:
            # Typically: category/section/filename
            if len(parts) >= 3:
                section = parts[-2]
                metadata["section"] = section.replace("_", " ").title()

        # Extract title from filename
        filename = path.stem  # Without extension
        # Clean filename: remove prefixes like "chapitre_", "titre_"
        clean_title = filename
        for prefix in ["chapitre_", "titre_", "livre_", "partie_", "section_"]:
            if clean_title.startswith(prefix):
                clean_title = clean_title[len(prefix):]

        metadata["title"] = clean_title.replace("_", " ").title()

        return metadata

    def _extract_from_content(self, content: str, file_path: str) -> Dict[str, Any]:
        """Extract metadata from document content"""
        metadata = {}

        # Limit content analysis to first 5000 chars for performance
        sample = content[:5000]

        # 1. Detect document type if not already detected
        if "category" not in metadata:
            doc_type = self._detect_document_type(sample)
            if doc_type:
                metadata["category"] = doc_type

        # 2. Extract articles references
        articles = self._extract_articles(sample)
        if articles:
            metadata["articles_references"] = articles
            # Store first article as primary reference
            if len(articles) > 0:
                metadata["article"] = articles[0]

        # 3. Extract comptes references (for plan comptable)
        comptes = self._extract_comptes(sample)
        if comptes:
            metadata["comptes_references"] = comptes
            if len(comptes) > 0:
                metadata["compte"] = comptes[0]

        # 4. Extract classe (for plan comptable)
        classes = self._extract_classes(sample)
        if classes:
            metadata["classes"] = classes
            if len(classes) > 0:
                metadata["classe"] = classes[0]

        # 5. Extract jurisdiction (for jurisprudence)
        if metadata.get("category") == "jurisprudence":
            jurisdiction = self._extract_jurisdiction(sample)
            if jurisdiction:
                metadata["jurisdiction"] = jurisdiction

            # Extract case number
            case_num = self._extract_case_number(sample)
            if case_num:
                metadata["case_number"] = case_num

        # 6. Extract date
        date = self._extract_date(sample)
        if date:
            metadata["date"] = date

        # 7. Extract legal topics
        topics = self._extract_legal_topics(content)
        if topics:
            metadata["legal_topics"] = topics

        # 8. Calculate content statistics
        metadata["content_length"] = len(content)
        metadata["word_count"] = len(content.split())

        return metadata

    def _detect_document_type(self, content: str) -> Optional[str]:
        """Detect document type from content patterns"""
        scores = {}

        for doc_type, patterns in self.type_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, content):
                    score += 1
            if score > 0:
                scores[doc_type] = score

        if scores:
            # Return type with highest score
            return max(scores.items(), key=lambda x: x[1])[0]

        return None

    def _extract_articles(self, content: str) -> List[str]:
        """Extract article references from content"""
        matches = self.article_pattern.findall(content)
        # Deduplicate and return first 10
        unique = list(dict.fromkeys(matches))
        return [f"Article {m}" for m in unique[:10]]

    def _extract_comptes(self, content: str) -> List[str]:
        """Extract compte references from content"""
        matches = self.compte_pattern.findall(content)
        unique = list(dict.fromkeys(matches))
        return [f"Compte {m}" for m in unique[:10]]

    def _extract_classes(self, content: str) -> List[str]:
        """Extract classe references from content"""
        matches = self.classe_pattern.findall(content)
        unique = list(dict.fromkeys(matches))
        return [f"Classe {m}" for m in unique]

    def _extract_jurisdiction(self, content: str) -> Optional[str]:
        """Extract jurisdiction from content"""
        for jurisdiction, pattern in self.jurisdiction_patterns.items():
            if pattern.search(content):
                return jurisdiction
        return None

    def _extract_case_number(self, content: str) -> Optional[str]:
        """Extract case/arrêt number from content"""
        match = self.case_number_pattern.search(content)
        if match:
            return match.group(1)
        return None

    def _extract_date(self, content: str) -> Optional[str]:
        """Extract date from content"""
        match = self.date_pattern.search(content)
        if match:
            day = match.group(1)
            month_fr = match.group(0).split()[1]
            year = match.group(2)

            # Convert French month to number
            months = {
                "janvier": "01", "février": "02", "mars": "03", "avril": "04",
                "mai": "05", "juin": "06", "juillet": "07", "août": "08",
                "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12"
            }
            month_num = months.get(month_fr.lower(), "01")

            return f"{year}-{month_num}-{day.zfill(2)}"
        return None

    def _extract_legal_topics(self, content: str) -> List[str]:
        """Extract legal topics from content based on keywords"""
        content_lower = content.lower()
        topics = []

        for topic, keywords in self.legal_topics_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    topics.append(topic)
                    break  # Topic found, move to next

        return topics[:5]  # Limit to top 5 topics


# Singleton instance
_metadata_extractor_instance: Optional[LegalMetadataExtractor] = None


def get_metadata_extractor() -> LegalMetadataExtractor:
    """Get singleton metadata extractor instance"""
    global _metadata_extractor_instance
    if _metadata_extractor_instance is None:
        _metadata_extractor_instance = LegalMetadataExtractor()
    return _metadata_extractor_instance
