"""
Veridict Core Engine Tests.
Verifies deterministic execution across all clinical cases and regulated domains.
"""

import json
from pathlib import Path
import pytest

from veridict.models.clinical import ClinicalCase
from veridict.models.review import Determination
from veridict.policies.registry import registry
from veridict.engine.orchestrator import default_engine


CASES_DIR = Path(__file__).parent.parent / "cases"


def test_registry_loaded():
    policies = registry.list_all()
    assert len(policies) >= 4
    assert registry.get("POL-PA-GLP1-2026") is not None
    assert registry.get("POL-PA-HUMIRA-RA-2026") is not None
    assert registry.get("POL-UM-CHESTPAIN-2026") is not None
    assert registry.get("POL-CLAIMS-MOD25-2026") is not None


def test_case_01_glp1_approval():
    case_path = CASES_DIR / "case_01_glp1_approve.json"
    with open(case_path, "r", encoding="utf-8") as f:
        case = ClinicalCase(**json.load(f))

    res = default_engine.run(case)
    assert res.proposer.determination == Determination.APPROVE
    assert res.critic.severity_max.value in ["LOW", "MEDIUM"]
    assert res.judge.final_determination == Determination.APPROVE
    assert not res.judge.human_in_the_loop_required
    assert res.audit_packet.is_valid
    assert len(res.audit_packet.nodes) == 5


def test_case_02_glp1_contraindication_denial():
    case_path = CASES_DIR / "case_02_glp1_deny_contraindication.json"
    with open(case_path, "r", encoding="utf-8") as f:
        case = ClinicalCase(**json.load(f))

    res = default_engine.run(case)
    # Must be denied due to MTC contraindication
    assert res.judge.final_determination == Determination.DENY
    assert "medullary thyroid" in res.judge.clinician_rationale.lower() or "exclusion" in res.judge.clinician_rationale.lower()


def test_case_03_humira_step_therapy_shortfall():
    case_path = CASES_DIR / "case_03_humira_step_therapy_fail.json"
    with open(case_path, "r", encoding="utf-8") as f:
        case = ClinicalCase(**json.load(f))

    res = default_engine.run(case)
    assert res.judge.final_determination in [Determination.DENY, Determination.REQUEST_MORE_INFO]
    assert "step" in res.judge.clinician_rationale.lower() or "dmard" in res.judge.clinician_rationale.lower()


def test_case_04_chest_pain_observation_reclassification():
    case_path = CASES_DIR / "case_04_chest_pain_observation_vs_inpatient.json"
    with open(case_path, "r", encoding="utf-8") as f:
        case = ClinicalCase(**json.load(f))

    res = default_engine.run(case)
    # Level of care must be partial approval / reclassification to observation
    assert res.judge.final_determination == Determination.PARTIAL_APPROVAL
    assert "observation" in res.judge.clinician_rationale.lower()
    assert "two-midnight" in res.judge.statutory_basis.lower() or "two-midnight" in res.judge.clinician_rationale.lower()


def test_case_05_modifier_25_unbundled_denial():
    case_path = CASES_DIR / "case_05_modifier_25_unbundled_audit.json"
    with open(case_path, "r", encoding="utf-8") as f:
        case = ClinicalCase(**json.load(f))

    res = default_engine.run(case)
    assert res.judge.final_determination == Determination.DENY
    assert "unbundle" in res.judge.clinician_rationale.lower() or "modifier 25" in res.judge.clinician_rationale.lower()


def test_case_06_hf_transitions_care_mgmt_approval():
    case_path = CASES_DIR / "case_06_hf_transitions_care_mgmt.json"
    with open(case_path, "r", encoding="utf-8") as f:
        case = ClinicalCase(**json.load(f))

    res = default_engine.run(case)
    assert res.judge.final_determination == Determination.APPROVE
    assert res.judge.patient_plain_language_notice is not None
