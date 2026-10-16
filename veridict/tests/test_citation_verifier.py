"""
Citation Verifier & Hallucination Guardrail Tests.
Tests exact string matching, offset resolution, and rejection of hallucinated quotes.
"""

from veridict.models.review import Citation
from veridict.engine.citation_verifier import CitationVerifier


SAMPLE_EHR = """
ENCOUNTER NOTE: 2026-10-01
PATIENT: Marcus Vance
VITALS: BP 132/84, HR 74, Weight 238 lbs, Height 5 ft 10 in.
Calculated Body Mass Index (BMI): 34.2 kg/m2 (Obese Class I).
LIFESTYLE: Engaged in structured calorie reduction for 7 months with dietitian.
FAMILY HISTORY: Negative for medullary thyroid carcinoma (MTC).
"""


def test_verbatim_exact_citation():
    quote = "Calculated Body Mass Index (BMI): 34.2 kg/m2"
    citation = Citation(
        criterion_id="CRIT-BMI",
        verbatim_quote=quote,
        source_section="VITALS",
        start_char=0,
        end_char=0,
    )
    res = CitationVerifier.verify_citation(citation, SAMPLE_EHR)
    assert res.is_verified is True
    assert res.confidence == 1.0
    assert SAMPLE_EHR[res.start_char:res.end_char] == quote


def test_hallucinated_citation_rejected():
    fake_quote = "Patient has severe morbid obesity with BMI of 48.5 and requires urgent bariatric surgery"
    citation = Citation(
        criterion_id="CRIT-BMI",
        verbatim_quote=fake_quote,
        source_section="VITALS",
        start_char=0,
        end_char=0,
    )
    res = CitationVerifier.verify_citation(citation, SAMPLE_EHR)
    assert res.is_verified is False
    assert res.verification_error is not None
    assert "Quote not found verbatim" in res.verification_error
    assert res.confidence <= 0.1
