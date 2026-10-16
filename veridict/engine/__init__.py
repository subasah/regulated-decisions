"""
Veridict Engine Package.
Exports Proposer, Critic, Judge, CitationVerifier, and DecisionEngine.
"""

from .citation_verifier import CitationVerifier
from .proposer import ProposerAgent
from .critic import CriticAgent
from .judge import JudgeAgent
from .audit_chain import AuditChainBuilder
from .orchestrator import DecisionEngine, CaseExecutionResult, default_engine

__all__ = [
    "CitationVerifier",
    "ProposerAgent",
    "CriticAgent",
    "JudgeAgent",
    "AuditChainBuilder",
    "DecisionEngine",
    "CaseExecutionResult",
    "default_engine",
]
