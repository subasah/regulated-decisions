"""
Veridict Audit Data Models.
Defines immutable SHA-256 hash chains, Merkle nodes, and CMS-0057-F auditable decision packets.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuditNode(BaseModel):
    stage: str = Field(..., description="Pipeline stage: INPUT_INGESTION, EVIDENCE_EXTRACTION, PROPOSER, CRITIC, JUDGE")
    node_id: str = Field(..., description="Unique node identifier in DAG")
    node_hash: str = Field(..., description="SHA-256 hash of this node's canonical payload and parent hash")
    parent_hash: Optional[str] = Field(None, description="SHA-256 hash of previous stage node")
    payload_summary: Dict[str, Any] = Field(default_factory=dict, description="Metadata and canonical digest of stage output")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class AuditPacket(BaseModel):
    audit_id: str = Field(..., description="Unique audit packet identifier")
    case_id: str = Field(..., description="Target clinical case ID")
    policy_id: str = Field(..., description="Evaluated policy ID")
    policy_version: str = Field(..., description="Evaluated policy version")
    genesis_hash: str = Field(..., description="Hash of the initial raw clinical input")
    terminal_hash: str = Field(..., description="Hash of the final judge verdict")
    merkle_root: str = Field(..., description="Combined Merkle root over the review trail")
    nodes: List[AuditNode] = Field(default_factory=list, description="Ordered nodes forming the verifiable hash chain")
    is_valid: bool = Field(True, description="Whether cryptographic integrity verification passed")
    cms_0057_f_compliant: bool = Field(True, description="Conforms to CMS Interoperability and Prior Authorization rule")
    tamper_check_passed: bool = Field(True, description="Whether recalculation matches all chained hashes")
    generated_at: str = Field(..., description="ISO 8601 packet generation timestamp")
