"""
Veridict Clinical Data Models.
Defines patient demographics, medical records, unstructured chart notes, and provenance spans.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .policy import PolicyDomain


class DocumentSnippet(BaseModel):
    snippet_id: str = Field(..., description="Unique snippet identifier")
    text: str = Field(..., description="Verbatim text extracted from source chart note")
    section: str = Field(..., description="EHR section name (e.g. History, Labs, Vitals, Assessment)")
    date: str = Field(..., description="Clinical encounter or note date")
    start_char: int = Field(..., description="Start character offset in unstructured text")
    end_char: int = Field(..., description="End character offset in unstructured text")


class PatientDemographics(BaseModel):
    patient_id: str = Field(..., description="De-identified patient ID")
    name: str = Field(..., description="De-identified patient name")
    age: int = Field(..., description="Age in years")
    gender: str = Field(..., description="Gender: M, F, Other")
    member_id: str = Field(..., description="Insurance Member ID")
    coverage_plan: str = Field(..., description="Plan type, e.g. Medicare Advantage HMO, Commercial PPO, Medicaid")


class ClinicalCase(BaseModel):
    case_id: str = Field(..., description="Unique case identifier, e.g. CASE-GLP1-001")
    title: str = Field(..., description="Case title or diagnosis headline")
    domain: PolicyDomain = Field(..., description="Regulated clinical domain")
    policy_id: str = Field(..., description="Policy ID to evaluate against")
    demographics: PatientDemographics = Field(..., description="Patient demographic record")
    requested_service: str = Field(..., description="Service, drug, or admission level requested")
    service_codes: List[str] = Field(default_factory=list, description="Associated CPT / HCPCS / ICD-10 codes")
    requesting_provider: str = Field(..., description="Requesting clinician and specialty")
    unstructured_note: str = Field(..., description="Full raw EHR progress note / clinical chart")
    structured_data: Dict[str, Any] = Field(default_factory=dict, description="Pre-extracted or parsed structured facts")
    documents: List[DocumentSnippet] = Field(default_factory=list, description="Indexed snippets with exact offsets")
