"""
Cryptographic Audit Trail Integrity & Tamper Detection Tests.
Verifies SHA-256 hash chaining, Merkle root consistency, and tamper detection.
"""

import json
from pathlib import Path
from veridict.models.clinical import ClinicalCase
from veridict.engine.orchestrator import default_engine
from veridict.engine.audit_chain import AuditChainBuilder


def test_audit_hash_chain_validity():
    case_path = Path(__file__).parent.parent / "cases" / "case_01_glp1_approve.json"
    with open(case_path, "r", encoding="utf-8") as f:
        case = ClinicalCase(**json.load(f))

    res = default_engine.run(case)
    packet = res.audit_packet

    assert packet.is_valid is True
    assert len(packet.nodes) == 5

    # Check that parent hashes correctly chain
    for i in range(1, len(packet.nodes)):
        assert packet.nodes[i].parent_hash == packet.nodes[i - 1].node_hash

    # Verify tamper check passes
    valid, err = AuditChainBuilder.verify_tamper(packet)
    assert valid is True
    assert err is None


def test_tamper_detection_on_altered_node():
    case_path = Path(__file__).parent.parent / "cases" / "case_01_glp1_approve.json"
    with open(case_path, "r", encoding="utf-8") as f:
        case = ClinicalCase(**json.load(f))

    res = default_engine.run(case)
    packet = res.audit_packet

    # Deliberately mutate a middle node's hash (simulating database alteration)
    tampered_packet = packet.model_copy(deep=True)
    tampered_packet.nodes[1].node_hash = "abcdef0123456789" * 4

    valid, err = AuditChainBuilder.verify_tamper(tampered_packet)
    assert valid is False
    assert err is not None
    assert "Hash break detected" in err
