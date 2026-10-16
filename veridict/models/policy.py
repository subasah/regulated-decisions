"""
Veridict Policy Data Models.
Defines machine-readable, computable clinical policies, rules, and criteria groups.
"""

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class PolicyDomain(str, Enum):
    PRIOR_AUTHORIZATION = "PRIOR_AUTHORIZATION"
    UTILIZATION_MANAGEMENT = "UTILIZATION_MANAGEMENT"
    CLAIMS_INTEGRITY = "CLAIMS_INTEGRITY"
    CARE_MANAGEMENT = "CARE_MANAGEMENT"


class CriterionType(str, Enum):
    INCLUSION = "INCLUSION"
    EXCLUSION = "EXCLUSION"
    STEP_THERAPY = "STEP_THERAPY"
    PREREQUISITE = "PREREQUISITE"
    DOCUMENTATION = "DOCUMENTATION"


class LogicalOperator(str, Enum):
    ALL_OF = "ALL_OF"
    ANY_OF = "ANY_OF"
    AT_LEAST_N = "AT_LEAST_N"


class ClinicalCriterion(BaseModel):
    criterion_id: str = Field(..., description="Unique criterion identifier, e.g. CRIT-BMI-01")
    name: str = Field(..., description="Human-readable title of the criterion")
    description: str = Field(..., description="Clinical definition of what must be proven")
    criterion_type: CriterionType = Field(..., description="Inclusion, exclusion, step therapy, etc.")
    field_name: str = Field(..., description="Clinical entity or field identifier")
    rule_operator: str = Field(..., description="Evaluation operator: >=, <=, ==, in, contains, exists, boolean")
    threshold: Any = Field(..., description="Target threshold value")
    unit: Optional[str] = Field(None, description="Clinical unit, e.g. kg/m2, months, mg/dL")
    lookback_days: Optional[int] = Field(None, description="Maximum age of clinical evidence in days")
    statutory_reference: Optional[str] = Field(None, description="Regulatory, clinical guideline, or NCD/LCD citation")
    is_mandatory: bool = Field(True, description="Whether satisfaction is strictly required")


class PolicyGroup(BaseModel):
    group_id: str = Field(..., description="Identifier for criteria group")
    title: str = Field(..., description="Title of this logical branch")
    operator: LogicalOperator = Field(LogicalOperator.ALL_OF, description="How criteria within group are combined")
    criteria_ids: List[str] = Field(default_factory=list, description="List of criterion IDs belonging to this group")
    min_matches: Optional[int] = Field(None, description="Required count if operator is AT_LEAST_N")


class PolicyDefinition(BaseModel):
    policy_id: str = Field(..., description="Unique policy identifier, e.g. POL-PA-GLP1-2026")
    title: str = Field(..., description="Official policy title")
    version: str = Field(..., description="Version string, e.g. 2026.1")
    effective_date: str = Field(..., description="ISO 8601 date")
    domain: PolicyDomain = Field(..., description="Regulated healthcare domain")
    regulatory_framework: str = Field(..., description="Statutory standard, e.g. CMS-0057-F, ERISA 503, URAC UM-1")
    target_codes: List[str] = Field(default_factory=list, description="CPT, HCPCS, ICD-10, or NDC codes governed")
    summary: str = Field(..., description="Clinical intent and scope summary")
    criteria: List[ClinicalCriterion] = Field(default_factory=list, description="Set of computable criteria")
    groups: List[PolicyGroup] = Field(default_factory=list, description="Logical groupings of criteria")
    statutory_appeal_timeline_days: int = Field(30, description="Statutory timeframe for standard appeal")
    expedited_appeal_timeline_hours: int = Field(72, description="Statutory timeframe for expedited/urgent appeal")
