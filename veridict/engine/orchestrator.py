"""
Veridict Engine Orchestrator.
Coordinates the end-to-end execution of the Proposer/Critic/Judge triad,
policy grounding, and cryptographic audit trail generation.
"""

from dataclasses import dataclass
import time
from typing import Optional

from veridict.models.audit import AuditPacket
from veridict.models.clinical import ClinicalCase
from veridict.models.policy import PolicyDefinition
from veridict.models.review import CriticOutput, JudgeVerdict, ProposerOutput
from veridict.policies.registry import registry
from veridict.engine.proposer import ProposerAgent
from veridict.engine.critic import CriticAgent
from veridict.engine.judge import JudgeAgent
from veridict.engine.audit_chain import AuditChainBuilder


@dataclass
class CaseExecutionResult:
    case: ClinicalCase
    policy: PolicyDefinition
    proposer: ProposerOutput
    critic: CriticOutput
    judge: JudgeVerdict
    audit_packet: AuditPacket
    execution_time_ms: float

    def to_dict(self):
        return {
            "case": self.case.model_dump(),
            "policy": self.policy.model_dump(),
            "proposer": self.proposer.model_dump(),
            "critic": self.critic.model_dump(),
            "judge": self.judge.model_dump(),
            "audit_packet": self.audit_packet.model_dump(),
            "execution_time_ms": self.execution_time_ms,
        }


class DecisionEngine:
    def __init__(
        self,
        proposer: Optional[ProposerAgent] = None,
        critic: Optional[CriticAgent] = None,
        judge: Optional[JudgeAgent] = None,
    ):
        self.proposer = proposer or ProposerAgent()
        self.critic = critic or CriticAgent()
        self.judge = judge or JudgeAgent()

    def run(
        self,
        case: ClinicalCase,
        policy: Optional[PolicyDefinition] = None,
    ) -> CaseExecutionResult:
        start_time = time.perf_counter()

        # 1. Resolve Policy
        if policy is None:
            policy = registry.get(case.policy_id)
            if policy is None:
                raise ValueError(
                    f"Policy '{case.policy_id}' not found in registry. "
                    f"Available: {[p.policy_id for p in registry.list_all()]}"
                )

        # 2. Stage A: Proposer Review
        proposer_output = self.proposer.evaluate(case, policy)

        # 3. Stage B: Critic Adversarial Review
        critic_output = self.critic.audit(case, policy, proposer_output)

        # 4. Stage C: Judge Adjudication
        judge_verdict = self.judge.adjudicate(case, policy, proposer_output, critic_output)

        # 5. Stage D: Cryptographic Audit Trail Generation
        audit_packet = AuditChainBuilder.build_chain(
            case, policy, proposer_output, critic_output, judge_verdict
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return CaseExecutionResult(
            case=case,
            policy=policy,
            proposer=proposer_output,
            critic=critic_output,
            judge=judge_verdict,
            audit_packet=audit_packet,
            execution_time_ms=elapsed_ms,
        )


# Global default engine instance
default_engine = DecisionEngine()
