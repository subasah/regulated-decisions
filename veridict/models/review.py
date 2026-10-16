"""
Veridict Review Models.
Defines structured proposer, critic, judge outputs, citations, and dual-audience rationales.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .policy import CriterionType


class Determination(str, Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    PARTIAL_APPROVAL = "PARTIAL_APPROVAL"
    ESCALATE_HUMAN = "ESCALATE_HUMAN"


class ChallengeSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKER = "BLOCKER"


class ChallengeType(str, Enum):
    UNGROUNDED_CITATION = "UNGROUNDED_CITATION"
    MISSING_EXCLUSION = "MISSING_EXCLUSION"
    STALE_DATA = "STALE_DATA"
    STEP_THERAPY_UNMET = "STEP_THERAPY_UNMET"
    INSUFFICIENT_DURATION = "INSUFFICIENT_DURATION"
    REGULATORY_NONCOMPLIANCE = "REGULATORY_NONCOMPLIANCE"
    HALLUCINATION = "HALLUCINATION"


class Citation(BaseModel):
    criterion_id: str = Field(..., description="Target criterion ID this citation satisfies")
    verbatim_quote: str = Field(..., description="Exact string quote from medical record")
    source_section: str = Field(..., description="Section of note where quote appears")
    start_char: int = Field(..., description="Start character offset in unstructured text")
    end_char: int = Field(..., description="End character offset in unstructured text")
    confidence: float = Field(1.0, description="Confidence of span grounding [0.0 - 1.0]")
    is_verified: bool = Field(False, description="Whether the verifier confirmed verbatim existence")
    verification_error: Optional[str] = Field(None, description="Explanation if verification failed")


class CriterionEvaluation(BaseModel):
    criterion_id: str = Field(..., description="Criterion identifier")
    criterion_name: str = Field(..., description="Human readable name")
    criterion_type: CriterionType = Field(..., description="Inclusion, exclusion, etc.")
    is_satisfied: bool = Field(..., description="Whether criterion condition evaluates to True")
    extracted_value: Any = Field(None, description="Concrete extracted value (e.g. 32.4, True, 6)")
    rationale: str = Field(..., description="Clinical justification for this criterion determination")
    citations: List[Citation] = Field(default_factory=list, description="Grounding citations verifying this fact")


class ProposerOutput(BaseModel):
    agent_id: str = Field("Proposer-ClinicalSpecialist-v1", description="Identifier of proposing agent")
    determination: Determination = Field(..., description="Proposed determination")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Proposer confidence score")
    criteria_evaluations: List[CriterionEvaluation] = Field(default_factory=list, description="Detailed criteria review")
    clinical_synthesis: str = Field(..., description="Synthesized clinical narrative supporting determination")
    primary_support_points: List[str] = Field(default_factory=list, description="Key clinical facts supporting approval/denial")
    missing_elements: List[str] = Field(default_factory=list, description="Any items requiring follow-up")
    timestamp: str = Field(..., description="ISO 8601 evaluation timestamp")


class CriticChallenge(BaseModel):
    challenge_id: str = Field(..., description="Unique challenge identifier")
    severity: ChallengeSeverity = Field(..., description="Impact severity of this challenge")
    criterion_id: Optional[str] = Field(None, description="Criterion challenged if applicable")
    challenge_type: ChallengeType = Field(..., description="Category of challenge")
    critique: str = Field(..., description="Detailed adversarial counterargument")
    source_evidence: Optional[str] = Field(None, description="Evidence in record supporting the counterargument")
    suggested_action: str = Field(..., description="Recommended correction or mitigation")


class CriticOutput(BaseModel):
    agent_id: str = Field("Critic-ComplianceAuditor-v1", description="Identifier of critic agent")
    counter_determination: Optional[Determination] = Field(None, description="Recommended alternative determination")
    severity_max: ChallengeSeverity = Field(..., description="Highest severity among challenges")
    challenges: List[CriticChallenge] = Field(default_factory=list, description="Adversarial challenges found")
    hallucination_detected: bool = Field(False, description="Flagged if any ungrounded claim was detected")
    compliance_risk_score: float = Field(0.0, ge=0.0, le=1.0, description="Risk index based on policy divergence")
    critique_summary: str = Field(..., description="Executive summary of compliance and safety review")
    timestamp: str = Field(..., description="ISO 8601 evaluation timestamp")


class ConsensusStatus(str, Enum):
    UNANIMOUS = "UNANIMOUS"
    CHALLENGE_ACCEPTED = "CHALLENGE_ACCEPTED"
    PROPOSER_UPHELD = "PROPOSER_UPHELD"
    SAFETY_OVERRIDE_ENFORCED = "SAFETY_OVERRIDE_ENFORCED"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"


class AppealRights(BaseModel):
    standard_appeal_deadline: str = Field(..., description="Statutory deadline date or window (e.g. 180 calendar days)")
    expedited_appeal_timeline: str = Field(..., description="Urgent clinical appeal turn-around (e.g. 72 hours)")
    statutory_governance: str = Field(..., description="Governing regulation (e.g. ERISA 29 CFR 2560.503-1 / CMS-0057-F)")
    independent_external_review_eligible: bool = Field(True, description="Whether state IRO / federal external review applies")
    how_to_appeal: str = Field(..., description="Explicit step-by-step instructions for filing an appeal")


class JudgeVerdict(BaseModel):
    agent_id: str = Field("Judge-ChiefMedicalOfficer-v1", description="Identifier of judge agent")
    final_determination: Determination = Field(..., description="Final binding determination")
    consensus_status: ConsensusStatus = Field(..., description="How consensus was reached or enforced")
    divergence_score: float = Field(0.0, ge=0.0, le=1.0, description="Divergence between proposer and critic [0=perfect agreement]")
    final_confidence: float = Field(..., ge=0.0, le=1.0, description="Final adjudicator confidence score")
    human_in_the_loop_required: bool = Field(False, description="Whether clinical human signoff is required")
    hitl_routing_reason: Optional[str] = Field(None, description="Reason for human triage if required")
    statutory_basis: str = Field(..., description="Legal and clinical policy clauses grounding this verdict")
    clinician_rationale: str = Field(..., description="Dense technical rationale with ICD/CPT codes, criteria, and evidence")
    patient_plain_language_notice: str = Field(..., description="CMS-0057-F compliant, 6th-grade reading level notice")
    appeal_rights: AppealRights = Field(..., description="Actionable statutory appeal information")
    timestamp: str = Field(..., description="ISO 8601 evaluation timestamp")
