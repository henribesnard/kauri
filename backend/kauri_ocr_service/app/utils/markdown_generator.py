"""
Markdown Generator - Converts OCR results to structured markdown
"""
from typing import Dict, List, Any, Optional
import re


class MarkdownGenerator:
    """Generate structured markdown from OCR results"""

    def __init__(self):
        pass

    def generate_from_ocr(self, ocr_result: Dict[str, Any], metadata: Optional[Dict] = None) -> str:
        """
        Generate markdown from OCR results

        Args:
            ocr_result: OCR processing results
            metadata: Optional document metadata

        Returns:
            Formatted markdown string
        """
        sections = []

        # Add header with metadata
        if metadata:
            sections.append(self._generate_header(metadata))

        # Add document text
        text = ocr_result.get('text', '')
        if text:
            # Try to detect structure
            structured_text = self._structure_text(text)
            sections.append(structured_text)

        # Add tables if present
        if 'tables' in ocr_result and ocr_result['tables']:
            sections.append("\n## Tables\n")
            for idx, table in enumerate(ocr_result['tables'], 1):
                sections.append(f"\n### Table {idx}\n")
                sections.append(self._format_table(table))

        # Add extracted entities if present
        if 'entities' in ocr_result and ocr_result['entities']:
            sections.append("\n## Extracted Information\n")
            sections.append(self._format_entities(ocr_result['entities']))

        # Add quality metrics
        if 'confidence_score' in ocr_result:
            sections.append(self._generate_metadata_footer(ocr_result))

        return "\n\n".join(sections)

    def _generate_header(self, metadata: Dict[str, Any]) -> str:
        """Generate markdown header with metadata"""
        lines = ["# Document"]

        if 'document_type' in metadata:
            doc_type = metadata['document_type'].replace('_', ' ').title()
            lines[0] = f"# {doc_type}"

        if 'filename' in metadata:
            lines.append(f"**File**: {metadata['filename']}")

        if 'date' in metadata:
            lines.append(f"**Date**: {metadata['date']}")

        return "\n".join(lines)

    def _structure_text(self, text: str) -> str:
        """
        Attempt to structure plain text by detecting headers, lists, etc.

        Args:
            text: Plain text from OCR

        Returns:
            Structured markdown text
        """
        lines = text.split('\n')
        structured_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                structured_lines.append('')
                continue

            # Detect potential headers (all caps, short lines)
            if line.isupper() and len(line) < 50:
                structured_lines.append(f"## {line.title()}")
            # Detect numbered lists
            elif re.match(r'^\d+[\.\)]\s', line):
                structured_lines.append(line)
            # Detect bullet points
            elif line.startswith(('•', '-', '*')):
                structured_lines.append(line)
            # Regular text
            else:
                structured_lines.append(line)

        return '\n'.join(structured_lines)

    def _format_table(self, table: Dict[str, Any]) -> str:
        """
        Format table data as markdown table

        Args:
            table: Table data with rows and columns

        Returns:
            Markdown table string
        """
        if 'table_data_markdown' in table:
            return table['table_data_markdown']

        # Generate from table_data_json if available
        if 'table_data_json' in table:
            data = table['table_data_json']
            if not data or not data[0]:
                return "*Empty table*"

            # Create markdown table
            lines = []

            # Header row
            header = data[0]
            lines.append('| ' + ' | '.join(str(cell) for cell in header) + ' |')
            lines.append('| ' + ' | '.join(['---'] * len(header)) + ' |')

            # Data rows
            for row in data[1:]:
                lines.append('| ' + ' | '.join(str(cell) for cell in row) + ' |')

            return '\n'.join(lines)

        return "*Table data not available*"

    def _format_entities(self, entities: List[Dict[str, Any]]) -> str:
        """
        Format extracted entities as markdown list

        Args:
            entities: List of entity dictionaries

        Returns:
            Markdown formatted entity list
        """
        if not entities:
            return "*No entities extracted*"

        lines = []
        grouped = {}

        # Group entities by type
        for entity in entities:
            entity_type = entity.get('entity_type', 'other')
            if entity_type not in grouped:
                grouped[entity_type] = []
            grouped[entity_type].append(entity)

        # Format each group
        for entity_type, items in grouped.items():
            type_label = entity_type.replace('_', ' ').title()
            lines.append(f"\n**{type_label}**:")
            for item in items:
                value = item.get('normalized_value') or item.get('raw_value', 'N/A')
                confidence = item.get('confidence_score')
                if confidence:
                    lines.append(f"- {value} (confidence: {confidence:.2%})")
                else:
                    lines.append(f"- {value}")

        return '\n'.join(lines)

    def _generate_metadata_footer(self, ocr_result: Dict[str, Any]) -> str:
        """Generate metadata footer with OCR quality metrics"""
        lines = ["\n---\n", "## Processing Information\n"]

        if 'confidence_score' in ocr_result:
            confidence = ocr_result['confidence_score']
            lines.append(f"- **Confidence Score**: {confidence:.2%}")

        if 'quality_score' in ocr_result:
            quality = ocr_result['quality_score']
            lines.append(f"- **Quality Score**: {quality:.2%}")

        if 'word_count' in ocr_result:
            lines.append(f"- **Word Count**: {ocr_result['word_count']}")

        if 'page_count' in ocr_result:
            lines.append(f"- **Pages**: {ocr_result['page_count']}")

        if 'processing_time_ms' in ocr_result:
            time_sec = ocr_result['processing_time_ms'] / 1000
            lines.append(f"- **Processing Time**: {time_sec:.2f}s")

        if 'engine' in ocr_result:
            lines.append(f"- **OCR Engine**: {ocr_result['engine']}")

        return '\n'.join(lines)


# Global instance
markdown_generator = MarkdownGenerator()
