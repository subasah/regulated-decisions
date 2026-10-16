"""
Veridict FastAPI Application Server.
Exposes RESTful endpoints for case execution, policy inspection, audit tamper verification,
benchmarking, and serves the interactive Recruiter Showcase & Documentation portal.
"""

from pathlib import Path
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from veridict.models.audit import AuditPacket
from veridict.models.clinical import ClinicalCase
from veridict.policies.registry import registry
from veridict.engine.orchestrator import default_engine
from veridict.engine.audit_chain import AuditChainBuilder

app = FastAPI(
    title="VERIDICT Decision Intelligence",
    description="Policy-Grounded & Adversarial Decision Intelligence Engine for Regulated Healthcare",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CASES_DIR = Path(__file__).parent.parent / "cases"


def load_all_cases() -> Dict[str, ClinicalCase]:
    cases = {}
    for f in CASES_DIR.glob("*.json"):
        try:
            import json
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                case = ClinicalCase(**data)
                cases[case.case_id] = case
        except Exception as e:
            pass
    return cases


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "engine": "Veridict Core v1.0.0",
        "policies_loaded": len(registry.list_all()),
        "cases_loaded": len(load_all_cases()),
    }


@app.get("/api/policies")
def list_policies():
    return [p.model_dump() for p in registry.list_all()]


@app.get("/api/policies/{policy_id}")
def get_policy(policy_id: str):
    p = registry.get(policy_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
    return p.model_dump()


@app.get("/api/cases")
def list_cases():
    cases = load_all_cases()
    return [
        {
            "case_id": c.case_id,
            "title": c.title,
            "domain": c.domain.value,
            "policy_id": c.policy_id,
            "patient_name": c.demographics.name,
            "patient_age": c.demographics.age,
            "coverage_plan": c.demographics.coverage_plan,
            "requested_service": c.requested_service,
            "service_codes": c.service_codes,
            "provider": c.requesting_provider,
        }
        for c in cases.values()
    ]


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    cases = load_all_cases()
    case = cases.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return case.model_dump()


class RunCaseRequest(BaseModel):
    case_id: Optional[str] = None
    custom_case: Optional[ClinicalCase] = None


@app.post("/api/run")
def execute_decision(req: RunCaseRequest):
    case: Optional[ClinicalCase] = None
    if req.custom_case:
        case = req.custom_case
    elif req.case_id:
        cases = load_all_cases()
        case = cases.get(req.case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {req.case_id} not found")
    else:
        raise HTTPException(status_code=400, detail="Must provide either case_id or custom_case")

    res = default_engine.run(case)
    return res.to_dict()


class TamperCheckRequest(BaseModel):
    audit_packet: AuditPacket
    tamper_node_index: Optional[int] = None
    tamper_value: Optional[str] = None


@app.post("/api/verify-tamper")
def verify_audit_trail(req: TamperCheckRequest):
    packet = req.audit_packet.model_copy(deep=True)
    if req.tamper_node_index is not None and 0 <= req.tamper_node_index < len(packet.nodes):
        tamper_val = req.tamper_value or ("0" * 64)
        packet.nodes[req.tamper_node_index].node_hash = tamper_val

    is_valid, error_msg = AuditChainBuilder.verify_tamper(packet)
    return {
        "is_valid": is_valid,
        "error": error_msg,
        "merkle_root": packet.merkle_root,
        "terminal_hash": packet.terminal_hash,
        "nodes_checked": len(packet.nodes),
    }


@app.get("/api/benchmark")
def run_benchmark():
    cases = load_all_cases()
    results = []
    total_start = time.perf_counter()

    for cid, case in sorted(cases.items()):
        res = default_engine.run(case)
        valid, err = AuditChainBuilder.verify_tamper(res.audit_packet)
        results.append({
            "case_id": case.case_id,
            "title": case.title,
            "domain": case.domain.value,
            "proposer_determination": res.proposer.determination.value,
            "critic_severity": res.critic.severity_max.value,
            "challenges_count": len(res.critic.challenges),
            "final_determination": res.judge.final_determination.value,
            "consensus_status": res.judge.consensus_status.value,
            "confidence": res.judge.final_confidence,
            "divergence": res.judge.divergence_score,
            "hitl_required": res.judge.human_in_the_loop_required,
            "tamper_valid": valid,
            "latency_ms": round(res.execution_time_ms, 2),
        })

    total_latency_ms = (time.perf_counter() - total_start) * 1000.0

    return {
        "summary": {
            "total_cases": len(results),
            "all_audit_trails_valid": all(r["tamper_valid"] for r in results),
            "avg_latency_ms": round(total_latency_ms / len(results), 2) if results else 0,
            "total_latency_ms": round(total_latency_ms, 2),
        },
        "results": results,
    }


# Static files mount for UI
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
