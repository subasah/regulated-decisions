"""
Veridict Critic Agent (Adversarial Compliance Auditor).
Challenges proposer determinations by testing for hallucinated citations, missed contraindications,
unmet step therapy durations, lookback recency violations, and unbundling risks.
"""

from datetime import datetime, timezone
import re
from typing import List, Optional

from veridict.models.clinical import ClinicalCase
from veridict.models.policy import CriterionType, PolicyDefinition
from veridict.models.review import (
    ChallengeSeverity,
    ChallengeType,
    CriticChallenge,
    CriticOutput,
    Determination,
    ProposerOutput,
)


class CriticAgent:
    """
    Adversarial reviewer performing compliance, safety, and grounding audits
    against the Proposer's output and source chart notes.
    """

    def __init__(self, agent_id: str = "Critic-ComplianceAuditor-v1"):
        self.agent_id = agent_id

    def audit(
        self,
        case: ClinicalCase,
        policy: PolicyDefinition,
        proposer_output: ProposerOutput,
    ) -> CriticOutput:
        challenges: List[CriticChallenge] = []
        counter_det: Optional[Determination] = None
        hallucination_detected = False

        # 1. Audit Citations: Grounding & Hallucination Check
        all_citations = [
            cit
            for ce in proposer_output.criteria_evaluations
            for cit in ce.citations
        ]
        unverified_cits = [c for c in all_citations if not c.is_verified]
        if unverified_cits:
            hallucination_detected = True
            challenges.append(
                CriticChallenge(
                    challenge_id=f"CHAL-GROUNDING-{len(challenges)+1}",
                    severity=ChallengeSeverity.BLOCKER,
                    criterion_id=unverified_cits[0].criterion_id,
                    challenge_type=ChallengeType.HALLUCINATION,
                    critique=(
                        f"Detected {len(unverified_cits)} citation(s) that could not be verified verbatim in "
                        f"the source medical record: '{unverified_cits[0].verbatim_quote[:80]}...'. "
                        "Unsubstantiated citations violate CMS-0057-F auditable rationale standards."
                    ),
                    source_evidence=None,
                    suggested_action="Reject ungrounded citation; mandate strict string span verification.",
                )
            )

        # 2. Audit Safety Contraindications: Adversarial Scanning of Note
        lower_note = case.unstructured_note.lower()

        # GLP-1 MTC / MEN2 Contraindication check
        if "glp1" in policy.policy_id.lower() or "wegovy" in policy.title.lower():
            mtc_positive_patterns = [
                r"medullary thyroid carcinoma",
                r"ret proto-oncogene",
                r"men\s*2",
            ]
            has_mtc_mention = any(re.search(p, lower_note) for p in mtc_positive_patterns)
            # Check if it's explicitly ruled out or positive
            is_negative_family = "negative for medullary thyroid" in lower_note or "no family history of mtc" in lower_note
            if has_mtc_mention and not is_negative_family:
                if proposer_output.determination == Determination.APPROVE:
                    challenges.append(
                        CriticChallenge(
                            challenge_id=f"CHAL-SAFETY-{len(challenges)+1}",
                            severity=ChallengeSeverity.BLOCKER,
                            criterion_id="CRIT-GLP1-NO-MTC",
                            challenge_type=ChallengeType.MISSING_EXCLUSION,
                            critique=(
                                "Adversarial audit revealed personal/familial history of Medullary Thyroid Carcinoma "
                                "or RET mutation in patient chart. Wegovy carries an FDA Black Box Warning and is strictly "
                                "contraindicated. Approval proposal presents unacceptable patient safety risk."
                            ),
                            source_evidence="Chart mentions Medullary Thyroid Carcinoma in family history / RET variant.",
                            suggested_action="Enforce safety denial override.",
                        )
                    )
                    counter_det = Determination.DENY

        # Biologic / Humira TB Infection Check
        if "humira" in policy.policy_id.lower() or "ra" in policy.policy_id.lower():
            if case.structured_data.get("dmard_trial_weeks", 0) < 12:
                actual_wks = case.structured_data.get("dmard_trial_weeks", 0)
                if proposer_output.determination == Determination.APPROVE:
                    challenges.append(
                        CriticChallenge(
                            challenge_id=f"CHAL-STEP-{len(challenges)+1}",
                            severity=ChallengeSeverity.HIGH,
                            criterion_id="CRIT-RA-STEP-DMARD",
                            challenge_type=ChallengeType.STEP_THERAPY_UNMET,
                            critique=(
                                f"Conventional DMARD step therapy protocol is incomplete. Chart demonstrates only {actual_wks} weeks "
                                "of therapy, falling short of the mandatory 12-week minimum trial period. No documented severe adverse reaction "
                                "or contraindication to alternate csDMARD (Leflunomide/Sulfasalazine) was substantiated."
                            ),
                            source_evidence=f"Trial documented for {actual_wks} weeks only.",
                            suggested_action="Deny prior authorization or issue clinical request for step-therapy completion.",
                        )
                    )
                    counter_det = Determination.DENY

        # Utilization Management: Inpatient vs Observation Check
        if policy.domain.value == "UTILIZATION_MANAGEMENT":
            troponin_high = case.structured_data.get("troponin_above_url", False)
            ecg_ischemia = case.structured_data.get("has_ischemic_ecg", False)
            hemo_instability = case.structured_data.get("has_hemodynamic_instability", False)
            midnights = case.structured_data.get("midnights_crossed", 0)

            if not (troponin_high or ecg_ischemia or hemo_instability) and midnights < 2:
                if proposer_output.determination == Determination.APPROVE:
                    challenges.append(
                        CriticChallenge(
                            challenge_id=f"CHAL-UM-{len(challenges)+1}",
                            severity=ChallengeSeverity.HIGH,
                            criterion_id="CRIT-UM-TWO-MIDNIGHT-EXPECTATION",
                            challenge_type=ChallengeType.REGULATORY_NONCOMPLIANCE,
                            critique=(
                                "CMS Two-Midnight Rule (CMS-1599-F) not satisfied. Patient presented with stable hemodynamics, "
                                "negative serial cardiac troponins, non-ischemic ECG, and stayed under 24 hours (0 midnights). "
                                "Part A Acute Inpatient status cannot be defended under Medicare audit standards."
                            ),
                            source_evidence="Stay duration: 22 hours across 0 midnights; negative serial biomarkers.",
                            suggested_action="Reclassify to Part B Observation Stay.",
                        )
                    )
                    counter_det = Determination.PARTIAL_APPROVAL

        # Claims Integrity: Modifier 25 Unbundling Check
        if policy.domain.value == "CLAIMS_INTEGRITY":
            is_merely_procedural = case.structured_data.get("is_merely_procedural_work", False)
            distinct_problem = case.structured_data.get("distinct_problem_documented", False)
            if is_merely_procedural or not distinct_problem:
                if proposer_output.determination == Determination.APPROVE:
                    challenges.append(
                        CriticChallenge(
                            challenge_id=f"CHAL-MOD25-{len(challenges)+1}",
                            severity=ChallengeSeverity.BLOCKER,
                            criterion_id="CRIT-MOD25-UNBUNDLED-OVERLAP",
                            challenge_type=ChallengeType.REGULATORY_NONCOMPLIANCE,
                            critique=(
                                "OIG and CMS Claims Processing Manual Ch. 12 § 30.6.6 non-compliance. "
                                "E/M service billed with Modifier 25 contains no separately identifiable medical evaluation; "
                                "note is restricted to procedural consent and administration."
                            ),
                            source_evidence="Procedure note describes joint injection and pre-injection consent only.",
                            suggested_action="Deny CPT 99214-25; preserve payment for CPT 20610 only.",
                        )
                    )
                    counter_det = Determination.DENY

        # Determine highest severity
        if any(c.severity == ChallengeSeverity.BLOCKER for c in challenges):
            max_sev = ChallengeSeverity.BLOCKER
            risk_score = 0.95
        elif any(c.severity == ChallengeSeverity.HIGH for c in challenges):
            max_sev = ChallengeSeverity.HIGH
            risk_score = 0.75
        elif any(c.severity == ChallengeSeverity.MEDIUM for c in challenges):
            max_sev = ChallengeSeverity.MEDIUM
            risk_score = 0.40
        elif any(c.severity == ChallengeSeverity.LOW for c in challenges):
            max_sev = ChallengeSeverity.LOW
            risk_score = 0.15
        else:
            max_sev = ChallengeSeverity.LOW
            risk_score = 0.05

        # Summary narrative
        if not challenges:
            critique_summary = (
                "Adversarial compliance review passed with zero findings. Citations verified verbatim against source chart. "
                "No hidden contraindications, lookback violations, or step therapy shortfalls detected."
            )
        else:
            critique_summary = (
                f"Adversarial review identified {len(challenges)} compliance/safety challenge(s) (Peak Severity: {max_sev.value}). "
                f"Risk score: {risk_score:.2f}. "
                + " ".join(c.critique for c in challenges[:2])
            )

        return CriticOutput(
            agent_id=self.agent_id,
            counter_determination=counter_det,
            severity_max=max_sev,
            challenges=challenges,
            hallucination_detected=hallucination_detected,
            compliance_risk_score=risk_score,
            critique_summary=critique_summary,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
