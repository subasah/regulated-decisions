"""
Veridict Judge Agent (Chief Medical Officer / Autonomous Adjudicator).
Synthesizes Proposer and Critic outputs, enforces safety overrides, calculates divergence,
and generates auditable dual-audience rationales (dense clinician vs CMS-compliant plain-language member notices).
"""

from datetime import datetime, timezone
from typing import Optional

from veridict.models.clinical import ClinicalCase
from veridict.models.policy import PolicyDefinition
from veridict.models.review import (
    AppealRights,
    ChallengeSeverity,
    ConsensusStatus,
    CriticOutput,
    Determination,
    JudgeVerdict,
    ProposerOutput,
)


class JudgeAgent:
    """
    Adjudicator presiding over the Proposer/Critic triad to produce
    the final legally defensible and clinically sound determination.
    """

    def __init__(self, agent_id: str = "Judge-ChiefMedicalOfficer-v1"):
        self.agent_id = agent_id

    def adjudicate(
        self,
        case: ClinicalCase,
        policy: PolicyDefinition,
        proposer: ProposerOutput,
        critic: CriticOutput,
    ) -> JudgeVerdict:
        # 1. Determine Consensus & Adjudication Branch
        has_blocker = critic.severity_max == ChallengeSeverity.BLOCKER
        has_high_challenge = critic.severity_max == ChallengeSeverity.HIGH
        proposer_det = proposer.determination
        critic_counter = critic.counter_determination

        hitl_required = False
        hitl_reason: Optional[str] = None

        if has_blocker:
            # Deterministic Safety Override: Blocker automatically overturns approval
            final_det = critic_counter or Determination.DENY
            status = ConsensusStatus.SAFETY_OVERRIDE_ENFORCED
            divergence = 0.95
            confidence = 0.98
            hitl_required = True
            hitl_reason = "Mandatory Medical Director signature required for adverse clinical safety override (Boxed Warning / Grounding Failure)."
        elif critic_counter is not None and critic_counter != proposer_det:
            # Critic recommended counter determination with HIGH severity
            final_det = critic_counter
            status = ConsensusStatus.CHALLENGE_ACCEPTED
            divergence = 0.80
            confidence = 0.92
            hitl_required = (final_det == Determination.DENY)
            if hitl_required:
                hitl_reason = "Adverse benefit determination requires designated medical director sign-off under ERISA 29 CFR 2560.503-1."
        elif has_high_challenge:
            final_det = Determination.REQUEST_MORE_INFO
            status = ConsensusStatus.HUMAN_ESCALATION
            divergence = 0.60
            confidence = 0.85
            hitl_required = True
            hitl_reason = "Divergent evidence threshold requires human clinical peer-to-peer inquiry."
        else:
            final_det = proposer_det
            status = ConsensusStatus.UNANIMOUS if not critic.challenges else ConsensusStatus.PROPOSER_UPHELD
            divergence = 0.05 if not critic.challenges else 0.20
            confidence = min(proposer.confidence_score, 0.99)
            # Under CMS-0057-F, standard approvals can be fully automated if criteria met
            hitl_required = False
            hitl_reason = None

        # 2. Construct Statutory Basis
        statutory_basis = (
            f"Adjudicated pursuant to {policy.regulatory_framework}. Governing clinical policy: {policy.title} "
            f"(Version {policy.version}, Effective: {policy.effective_date}). "
            f"Adjudication protocol: Veridict Multi-Agent Triad with Deterministic Safety Constraints."
        )

        # 3. Generate Clinician / Auditor Rationale (Dense, technical, code-grounded)
        clinician_rationale = self._generate_clinician_rationale(
            case, policy, proposer, critic, final_det, status
        )

        # 4. Generate Patient / Member Plain-Language Notice (CMS-0057-F 6th-grade reading level)
        patient_notice = self._generate_patient_notice(
            case, policy, final_det, status, critic
        )

        # 5. Formulate Statutory Appeal Rights
        appeal_rights = AppealRights(
            standard_appeal_deadline=f"{policy.statutory_appeal_timeline_days} calendar days from receipt of this notice",
            expedited_appeal_timeline=f"{policy.expedited_appeal_timeline_hours} hours for urgent clinical scenarios",
            statutory_governance=policy.regulatory_framework,
            independent_external_review_eligible=True,
            how_to_appeal=(
                "You or your treating physician may request a free copy of the clinical criteria used and file an appeal "
                "by submitting an appeal form online at https://appeals.veridicthealth.example.com or calling Member Services at 1-800-555-0199. "
                "If your physician states that waiting could seriously jeopardize your health, you may request an Expedited Urgent Appeal."
            ),
        )

        return JudgeVerdict(
            agent_id=self.agent_id,
            final_determination=final_det,
            consensus_status=status,
            divergence_score=divergence,
            final_confidence=confidence,
            human_in_the_loop_required=hitl_required,
            hitl_routing_reason=hitl_reason,
            statutory_basis=statutory_basis,
            clinician_rationale=clinician_rationale,
            patient_plain_language_notice=patient_notice,
            appeal_rights=appeal_rights,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _generate_clinician_rationale(
        self,
        case: ClinicalCase,
        policy: PolicyDefinition,
        proposer: ProposerOutput,
        critic: CriticOutput,
        verdict: Determination,
        status: ConsensusStatus,
    ) -> str:
        lines = [
            f"CLINICAL ADJUDICATION SUMMARY — CASE {case.case_id}",
            f"Requested Service: {case.requested_service} (Codes: {', '.join(case.service_codes)})",
            f"Governing Policy: {policy.policy_id} v{policy.version} ({policy.title})",
            f"Determination: {verdict.value} (Consensus Status: {status.value})",
            "",
            "1. CRITERIA EVALUATION & EVIDENCE SYNTHESIS:",
        ]

        for ce in proposer.criteria_evaluations:
            mark = "[SATISFIED]" if ce.is_satisfied else "[UNMET]"
            lines.append(f"  * {ce.criterion_name} {mark}: {ce.rationale}")
            for cit in ce.citations:
                lines.append(f"      - Citation: \"{cit.verbatim_quote}\" [Offset {cit.start_char}-{cit.end_char}, Section: {cit.source_section}]")

        lines.append("")
        lines.append("2. ADVERSARIAL COMPLIANCE & SAFETY AUDIT:")
        if not critic.challenges:
            lines.append("  * Zero compliance violations or contraindication flags detected.")
        else:
            for ch in critic.challenges:
                lines.append(f"  * [{ch.severity.value}] {ch.challenge_type.value}: {ch.critique}")
                if ch.source_evidence:
                    lines.append(f"      - Record Evidence: {ch.source_evidence}")

        lines.append("")
        lines.append(f"3. FINAL MEDICAL JUDGMENT: {verdict.value}")
        if verdict == Determination.APPROVE:
            lines.append(
                "  Medical necessity criteria are met in full. Service is approved in accordance with evidence-based "
                "clinical guidelines and statutory coverage terms."
            )
        elif verdict == Determination.PARTIAL_APPROVAL:
            lines.append(
                "  Admitted level of care does not meet inpatient severity criteria under CMS-1599-F (Two-Midnight Rule). "
                "Reclassified to Outpatient Observation Stay. Observation billing substantiated."
            )
        else:
            lines.append(
                f"  Service is denied pursuant to policy criteria. Unmet clinical prerequisites or safety contraindications "
                f"preclude coverage authorization at this time."
            )

        return "\n".join(lines)

    def _generate_patient_notice(
        self,
        case: ClinicalCase,
        policy: PolicyDefinition,
        verdict: Determination,
        status: ConsensusStatus,
        critic: CriticOutput,
    ) -> str:
        name = case.demographics.name
        service = case.requested_service

        if verdict == Determination.APPROVE:
            return (
                f"Dear {name},\n\n"
                f"Great news: We have approved your doctor's request for {service}.\n\n"
                f"Why was this approved?\n"
                f"Our clinical team reviewed your medical chart and confirmed that you meet all health guidelines for this treatment. "
                f"Your recent lab results, visit notes, and treatment history show this medication/service is medically appropriate for you.\n\n"
                f"What happens next?\n"
                f"Your doctor has been notified and you can now receive this service. You do not need to take any action."
            )

        if verdict == Determination.PARTIAL_APPROVAL:
            return (
                f"Dear {name},\n\n"
                f"We are writing to update you about your recent hospital stay for {service}.\n\n"
                f"What was decided?\n"
                f"Your care at the hospital has been approved under Observation Status instead of a full Inpatient Admission.\n\n"
                f"Why was this decided?\n"
                f"Medicare rules (the Two-Midnight Rule) require that a full inpatient hospital stay is for patients who need "
                f"intensive hospital care that lasts over at least two midnights. During your stay, your heart tests and vital signs "
                f"were stable and you safely completed your tests in under 24 hours. Because you did not need multi-day acute care, "
                f"your stay is covered under your outpatient observation benefits.\n\n"
                f"What does this mean for you?\n"
                f"Your care is covered. If you disagree, you and your doctor have the legal right to appeal. Please see below for your appeal rights."
            )

        # Denials / Adverse determinations
        reasons_plain = []
        if any(c.challenge_type.value == "MISSING_EXCLUSION" for c in critic.challenges):
            reasons_plain.append(
                "A major safety concern was found in your chart (such as a personal or family history of specific thyroid conditions). "
                "Because of FDA safety warnings, taking this medicine could be dangerous to your health."
            )
        elif any(c.challenge_type.value == "STEP_THERAPY_UNMET" for c in critic.challenges):
            reasons_plain.append(
                "Our health plan guidelines require trying standard, well-established first-line medications (such as oral therapy for at least 12 weeks) "
                "before advancing to this specialty biologic drug. Your records showed fewer than 12 weeks of trial."
            )
        elif any(c.challenge_type.value == "REGULATORY_NONCOMPLIANCE" for c in critic.challenges):
            reasons_plain.append(
                "The clinical documentation sent by your provider did not show a separate medical evaluation outside of the routine procedure performed."
            )
        else:
            reasons_plain.append(
                "The records provided by your doctor did not show that you meet all required clinical milestones set by your health plan's medical policy."
            )

        reason_str = " ".join(reasons_plain)

        return (
            f"Dear {name},\n\n"
            f"We are writing to inform you that we could not approve the coverage request submitted by your doctor for {service}.\n\n"
            f"Why was coverage denied?\n"
            f"{reason_str}\n\n"
            f"What other options do you have?\n"
            f"We encourage you to talk with your doctor about other treatment choices that may be safe and covered under your plan. "
            f"Your doctor can also submit additional records or ask to speak directly with our medical director in a Peer-to-Peer discussion.\n\n"
            f"You have the right to appeal this decision.\n"
            f"If you or your doctor believe this decision is incorrect, you can appeal. You will not lose coverage for other health services "
            f"because you filed an appeal."
        )
