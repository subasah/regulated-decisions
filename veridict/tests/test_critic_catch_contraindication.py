"""
Adversarial Safety Tests: Proposer-Critic Challenge and Override.
Tests that if a Proposer erroneously proposes APPROVE when a contraindication exists,
the Critic raises a BLOCKER challenge and the Judge enforces a safety denial override.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from veridict.models.clinical import ClinicalCase
from veridict.models.review import (
    ChallengeSeverity,
    ConsensusStatus,
    CriterionEvaluation,
    Determination,
    ProposerOutput,
)
from veridict.policies.registry import registry
from veridict.engine.critic import CriticAgent
from veridict.engine.judge import JudgeAgent


def test_adversarial_critic_overrides_rogue_proposer():
    # Load case 2 (Eleanor Vance - MTC in family history)
    case_path = Path(__file__).parent.parent / "cases" / "case_02_glp1_deny_contraindication.json"
    with open(case_path, "r", encoding="utf-8") as f:
        case = ClinicalCase(**json.load(f))

    policy = registry.get(case.policy_id)
    assert policy is not None

    # Construct an adversarial / rogue proposer that overlooked the contraindication
    rogue_proposer_output = ProposerOutput(
        agent_id="Rogue-Proposer-BiasedTowardsApproval",
        determination=Determination.APPROVE,
        confidence_score=0.97,
        criteria_evaluations=[
            CriterionEvaluation(
                criterion_id="CRIT-GLP1-BMI-HIGH",
                criterion_name="BMI >= 30",
                criterion_type="INCLUSION",
                is_satisfied=True,
                extracted_value=34.0,
                rationale="BMI is 34.0, meeting obesity threshold.",
                citations=[],
            ),
            CriterionEvaluation(
                criterion_id="CRIT-GLP1-LIFESTYLE-TRIAL",
                criterion_name="Lifestyle Trial >= 6 Months",
                criterion_type="STEP_THERAPY",
                is_satisfied=True,
                extracted_value=9,
                rationale="9 months of dieting documented.",
                citations=[],
            ),
        ],
        clinical_synthesis="Patient has high BMI and completed lifestyle trial; recommending approval.",
        primary_support_points=["High BMI", "Dietary trial"],
        missing_elements=[],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    critic = CriticAgent()
    critic_output = critic.audit(case, policy, rogue_proposer_output)

    # Assert that Critic caught the contraindication
    assert critic_output.severity_max == ChallengeSeverity.BLOCKER
    assert critic_output.counter_determination == Determination.DENY
    assert any(c.challenge_type.value == "MISSING_EXCLUSION" for c in critic_output.challenges)

    # Now let Judge adjudicate this debate
    judge = JudgeAgent()
    verdict = judge.adjudicate(case, policy, rogue_proposer_output, critic_output)

    # Assert that Judge enforced safety override and rejected the rogue proposer
    assert verdict.final_determination == Determination.DENY
    assert verdict.consensus_status == ConsensusStatus.SAFETY_OVERRIDE_ENFORCED
    assert verdict.human_in_the_loop_required is True
    assert verdict.divergence_score >= 0.90
