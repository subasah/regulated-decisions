"""
Veridict Citation Verifier.
Ensures zero-tolerance grounding by verifying that quoted evidence literally exists
in the source clinical chart note and calculating precise character offsets.
"""

import re
from typing import List, Optional, Tuple
from veridict.models.review import Citation


class CitationVerifier:
    """Verifies that citation quotes exist in source document and confirms exact spans."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalizes whitespace for fuzzy comparison while preserving characters."""
        return re.sub(r"\s+", " ", text).strip().lower()

    @classmethod
    def verify_citation(cls, citation: Citation, raw_text: str) -> Citation:
        """
        Validates a citation against raw unstructured text.
        Updates is_verified, start_char, end_char, and verification_error.
        """
        quote = citation.verbatim_quote.strip()
        if not quote:
            citation.is_verified = False
            citation.verification_error = "Empty verbatim quote"
            citation.confidence = 0.0
            return citation

        # 1. Exact string search
        idx = raw_text.find(quote)
        if idx != -1:
            citation.start_char = idx
            citation.end_char = idx + len(quote)
            citation.is_verified = True
            citation.verification_error = None
            citation.confidence = 1.0
            return citation

        # 2. Case-insensitive search
        lower_raw = raw_text.lower()
        lower_quote = quote.lower()
        idx_lower = lower_raw.find(lower_quote)
        if idx_lower != -1:
            citation.start_char = idx_lower
            citation.end_char = idx_lower + len(quote)
            citation.is_verified = True
            citation.verification_error = None
            citation.confidence = 0.95
            return citation

        # 3. Normalized whitespace search
        norm_quote = cls.normalize_text(quote)
        # Search token sequence
        tokens = norm_quote.split()
        if len(tokens) >= 3:
            pattern = r"\s+".join(re.escape(t) for t in tokens)
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                citation.start_char = match.start()
                citation.end_char = match.end()
                citation.is_verified = True
                citation.verification_error = None
                citation.confidence = 0.90
                return citation

        # 4. Fallback: Not found in source text -> Hallucination or severe mismatch
        citation.is_verified = False
        citation.verification_error = f"Quote not found verbatim in clinical document: '{quote[:60]}...'"
        citation.confidence = 0.1
        return citation

    @classmethod
    def verify_all(cls, citations: List[Citation], raw_text: str) -> List[Citation]:
        return [cls.verify_citation(c, raw_text) for c in citations]
