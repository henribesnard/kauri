"""
OHADA Compliance Validator
Validates financial documents against OHADA standards
"""
from typing import Dict, List, Any, Optional
import re
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class OHADAValidator:
    """Validator for OHADA compliance"""

    # SYSCOHADA account codes regex patterns
    ACCOUNT_CODE_PATTERN = re.compile(r'^\d{1,8}$')

    # OHADA financial statement types
    FINANCIAL_STATEMENTS = [
        'balance_sheet',      # Bilan
        'income_statement',   # Compte de résultat
        'cash_flow',         # Tableau des flux de trésorerie
        'notes'              # Notes annexes
    ]

    # OHADA account classes
    ACCOUNT_CLASSES = {
        '1': 'Comptes de ressources durables',
        '2': 'Comptes d\'actif immobilisé',
        '3': 'Comptes de stocks',
        '4': 'Comptes de tiers',
        '5': 'Comptes de trésorerie',
        '6': 'Comptes de charges',
        '7': 'Comptes de produits',
        '8': 'Comptes des autres charges et des autres produits'
    }

    def __init__(self):
        self.ohada_countries = settings.ohada_countries_list
        self.vat_rates = settings.vat_rates_list

    def validate_document(
        self,
        document_data: Dict[str, Any],
        country_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a document for OHADA compliance

        Args:
            document_data: Extracted document data
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            Validation results with errors and warnings
        """
        errors = []
        warnings = []
        is_compliant = True

        # Check if country is OHADA member
        if country_code and country_code not in self.ohada_countries:
            warnings.append(f"Country {country_code} is not an OHADA member state")

        # Validate based on document type
        doc_type = document_data.get('document_type')

        if doc_type == 'invoice':
            invoice_validation = self._validate_invoice(document_data)
            errors.extend(invoice_validation['errors'])
            warnings.extend(invoice_validation['warnings'])

        elif doc_type == 'balance_sheet':
            balance_validation = self._validate_balance_sheet(document_data)
            errors.extend(balance_validation['errors'])
            warnings.extend(balance_validation['warnings'])

        elif doc_type == 'journal_entry':
            journal_validation = self._validate_journal_entry(document_data)
            errors.extend(journal_validation['errors'])
            warnings.extend(journal_validation['warnings'])

        # Check account codes if present
        if 'account_codes' in document_data:
            account_validation = self._validate_account_codes(document_data['account_codes'])
            errors.extend(account_validation['errors'])
            warnings.extend(account_validation['warnings'])

        # Validate financial amounts
        if 'financial_data' in document_data:
            amount_validation = self._validate_amounts(document_data['financial_data'])
            errors.extend(amount_validation['errors'])
            warnings.extend(amount_validation['warnings'])

        is_compliant = len(errors) == 0

        return {
            'is_compliant': is_compliant,
            'errors': errors,
            'warnings': warnings,
            'validation_date': None,  # TODO: Add timestamp
            'standard': 'SYSCOHADA'
        }

    def _validate_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate invoice for OHADA compliance"""
        errors = []
        warnings = []

        # Required fields for OHADA invoice
        required_fields = [
            'invoice_number',
            'invoice_date',
            'issuer',
            'recipient',
            'line_items',
            'total_amount'
        ]

        for field in required_fields:
            if field not in invoice_data or not invoice_data[field]:
                errors.append(f"Missing required field: {field}")

        # Validate VAT
        if 'vat_rate' in invoice_data:
            vat_rate = invoice_data['vat_rate']
            if vat_rate not in self.vat_rates and vat_rate != 0:
                warnings.append(f"Unusual VAT rate: {vat_rate}. Expected: {self.vat_rates}")

        # Validate VAT calculation
        if all(k in invoice_data for k in ['amount_ht', 'vat_rate', 'vat_amount', 'total_amount']):
            amount_ht = invoice_data['amount_ht']
            vat_rate = invoice_data['vat_rate']
            vat_amount = invoice_data['vat_amount']
            total_amount = invoice_data['total_amount']

            expected_vat = amount_ht * vat_rate
            expected_total = amount_ht + expected_vat

            # Allow 1% tolerance for rounding
            if abs(vat_amount - expected_vat) > amount_ht * 0.01:
                errors.append(f"VAT calculation mismatch. Expected: {expected_vat}, Found: {vat_amount}")

            if abs(total_amount - expected_total) > amount_ht * 0.01:
                errors.append(f"Total amount mismatch. Expected: {expected_total}, Found: {total_amount}")

        # Validate issuer tax ID
        if 'issuer' in invoice_data:
            issuer = invoice_data['issuer']
            if 'tax_id' not in issuer or not issuer['tax_id']:
                errors.append("Issuer tax ID is required for OHADA invoice")

        return {'errors': errors, 'warnings': warnings}

    def _validate_balance_sheet(self, balance_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate balance sheet for OHADA compliance"""
        errors = []
        warnings = []

        # Check balance equation: Assets = Liabilities + Equity
        if all(k in balance_data for k in ['total_assets', 'total_liabilities', 'total_equity']):
            assets = balance_data['total_assets']
            liabilities = balance_data['total_liabilities']
            equity = balance_data['total_equity']

            if abs(assets - (liabilities + equity)) > 0.01:
                errors.append(f"Balance sheet not balanced: Assets ({assets}) != Liabilities + Equity ({liabilities + equity})")

        # Check for required sections
        required_sections = ['assets', 'liabilities', 'equity']
        for section in required_sections:
            if section not in balance_data:
                warnings.append(f"Missing balance sheet section: {section}")

        return {'errors': errors, 'warnings': warnings}

    def _validate_journal_entry(self, entry_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate journal entry for OHADA compliance"""
        errors = []
        warnings = []

        # Check debit = credit
        if all(k in entry_data for k in ['total_debit', 'total_credit']):
            debit = entry_data['total_debit']
            credit = entry_data['total_credit']

            if abs(debit - credit) > 0.01:
                errors.append(f"Journal entry not balanced: Debit ({debit}) != Credit ({credit})")

        # Validate required fields
        required_fields = ['date', 'journal_code', 'description', 'lines']
        for field in required_fields:
            if field not in entry_data:
                errors.append(f"Missing required field: {field}")

        # Validate journal lines
        if 'lines' in entry_data:
            for idx, line in enumerate(entry_data['lines'], 1):
                if 'account_code' not in line:
                    errors.append(f"Line {idx}: Missing account code")

                if 'debit' not in line and 'credit' not in line:
                    errors.append(f"Line {idx}: Must have either debit or credit")

                if 'debit' in line and 'credit' in line and line['debit'] > 0 and line['credit'] > 0:
                    errors.append(f"Line {idx}: Cannot have both debit and credit")

        return {'errors': errors, 'warnings': warnings}

    def _validate_account_codes(self, account_codes: List[str]) -> Dict[str, List[str]]:
        """Validate SYSCOHADA account codes"""
        errors = []
        warnings = []

        for code in account_codes:
            # Check format
            if not self.ACCOUNT_CODE_PATTERN.match(code):
                errors.append(f"Invalid account code format: {code}")
                continue

            # Check account class (first digit)
            account_class = code[0]
            if account_class not in self.ACCOUNT_CLASSES:
                errors.append(f"Invalid account class: {account_class} in code {code}")

        return {'errors': errors, 'warnings': warnings}

    def _validate_amounts(self, financial_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate financial amounts"""
        errors = []
        warnings = []

        # Check for negative amounts where not expected
        amount_fields = ['total_amount', 'amount_ht', 'vat_amount']
        for field in amount_fields:
            if field in financial_data and financial_data[field] < 0:
                warnings.append(f"Negative amount detected for {field}: {financial_data[field]}")

        # Check currency
        if 'currency' in financial_data:
            currency = financial_data['currency']
            # OHADA zone primarily uses XOF (West) and XAF (Central)
            ohada_currencies = ['XOF', 'XAF']
            if currency not in ohada_currencies:
                warnings.append(f"Non-OHADA currency detected: {currency}. Expected: {ohada_currencies}")

        return {'errors': errors, 'warnings': warnings}

    def validate_account_code(self, account_code: str) -> Dict[str, Any]:
        """
        Validate a single SYSCOHADA account code

        Args:
            account_code: Account code to validate

        Returns:
            Validation result with details
        """
        if not self.ACCOUNT_CODE_PATTERN.match(account_code):
            return {
                'is_valid': False,
                'error': 'Invalid format. Must be 1-8 digits.',
                'account_class': None,
                'class_description': None
            }

        account_class = account_code[0]
        class_description = self.ACCOUNT_CLASSES.get(account_class, 'Unknown')

        return {
            'is_valid': True,
            'account_code': account_code,
            'account_class': account_class,
            'class_description': class_description,
            'error': None
        }


# Global validator instance
ohada_validator = OHADAValidator()
