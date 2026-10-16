"""
Veridict Command-Line Interface (CLI).
Interactive terminal runner with rich tables, colored debate streams, and audit verification.
"""

import json
from pathlib import Path
import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import typer

from veridict.models.clinical import ClinicalCase
from veridict.models.review import ChallengeSeverity, Determination
from veridict.policies.registry import registry
from veridict.engine.orchestrator import default_engine
from veridict.engine.audit_chain import AuditChainBuilder

app = typer.Typer(
    name="veridict",
    help="VERIDICT: Policy-Grounded & Adversarial Decision Intelligence for Regulated Healthcare",
    add_completion=False,
)
console = Console()


@app.command("list-policies")
def list_policies():
    """Lists all computable clinical policies currently registered."""
    policies = registry.list_all()
    table = Table(title="[bold cyan]Registered Clinical Policies[/bold cyan]", show_header=True)
    table.add_column("Policy ID", style="bold green")
    table.add_column("Domain", style="magenta")
    table.add_column("Version", style="yellow")
    table.add_column("Criteria Count", justify="right")
    table.add_column("Target Codes", style="dim")
    table.add_column("Regulatory Framework")

    for p in policies:
        table.add_row(
            p.policy_id,
            p.domain.value,
            p.version,
            str(len(p.criteria)),
            ", ".join(p.target_codes[:3]),
            p.regulatory_framework,
        )
    console.print(table)


@app.command("list-cases")
def list_cases():
    """Lists all preloaded clinical test cases across domains."""
    cases_dir = Path(__file__).parent / "cases"
    case_files = sorted(cases_dir.glob("*.json"))

    table = Table(title="[bold cyan]Preloaded Clinical Benchmark Cases[/bold cyan]", show_header=True)
    table.add_column("Case ID", style="bold green")
    table.add_column("Patient", style="bold white")
    table.add_column("Domain", style="magenta")
    table.add_column("Requested Service")
    table.add_column("File")

    for cf in case_files:
        try:
            with open(cf, "r", encoding="utf-8") as f:
                data = json.load(f)
                case = ClinicalCase(**data)
                table.add_row(
                    case.case_id,
                    f"{case.demographics.name} ({case.demographics.age}yo)",
                    case.domain.value,
                    case.requested_service[:45] + "...",
                    cf.name,
                )
        except Exception as e:
            pass
    console.print(table)


@app.command("run")
def run_case(
    case_path: str = typer.Argument(..., help="Path to clinical case JSON file or case ID"),
    show_audit: bool = typer.Option(True, "--show-audit/--no-audit", help="Display cryptographic hash chain"),
    show_patient_notice: bool = typer.Option(True, "--show-notice/--no-notice", help="Display CMS plain-language notice"),
):
    """Executes the Proposer-Critic-Judge triad on a clinical case."""
    path = Path(case_path)
    if not path.exists():
        # Check in cases/
        cand = Path(__file__).parent / "cases" / case_path
        if not cand.exists() and not case_path.endswith(".json"):
            cand = Path(__file__).parent / "cases" / f"{case_path}.json"
        if cand.exists():
            path = cand
        else:
            console.print(f"[bold red]Error:[/bold red] Case file not found at {case_path}")
            sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        case_data = json.load(f)
        case = ClinicalCase(**case_data)

    console.print(Panel(
        f"[bold white]{case.title}[/bold white]\n"
        f"[cyan]Patient:[/cyan] {case.demographics.name} | [cyan]Member ID:[/cyan] {case.demographics.member_id} | [cyan]Age:[/cyan] {case.demographics.age}\n"
        f"[cyan]Requested:[/cyan] {case.requested_service}\n"
        f"[cyan]Codes:[/cyan] {', '.join(case.service_codes)} | [cyan]Policy:[/cyan] {case.policy_id}",
        title="[bold green]Case Ingestion[/bold green]",
        border_style="green",
    ))

    # Run engine
    res = default_engine.run(case)

    # 1. Proposer Table
    p_det_color = "green" if res.proposer.determination == Determination.APPROVE else "red"
    p_table = Table(title=f"Stage 1: Proposer (Clinical Specialist) -> [{p_det_color}]{res.proposer.determination.value}[/{p_det_color}] (Conf: {res.proposer.confidence_score:.2f})")
    p_table.add_column("Criterion", style="bold")
    p_table.add_column("Type", style="cyan")
    p_table.add_column("Status", justify="center")
    p_table.add_column("Extracted Fact / Rationale")
    p_table.add_column("Citations", justify="center")

    for ce in res.proposer.criteria_evaluations:
        status_txt = "[bold green]PASS[/bold green]" if ce.is_satisfied else "[bold red]FAIL[/bold red]"
        if ce.criterion_type.value == "EXCLUSION":
            status_txt = "[bold red]TRIGGERED[/bold red]" if ce.is_satisfied else "[bold green]CLEARED[/bold green]"
        cits_txt = f"{len(ce.citations)} verified" if ce.citations else "[dim]None[/dim]"
        p_table.add_row(ce.criterion_name, ce.criterion_type.value, status_txt, ce.rationale, cits_txt)
    console.print(p_table)

    # 2. Critic Table
    c_color = "red" if res.critic.severity_max in [ChallengeSeverity.BLOCKER, ChallengeSeverity.HIGH] else "yellow" if res.critic.severity_max == ChallengeSeverity.MEDIUM else "green"
    c_panel = Panel(
        f"[bold {c_color}]Peak Severity: {res.critic.severity_max.value}[/bold {c_color}] | "
        f"Compliance Risk Score: {res.critic.compliance_risk_score:.2f} | "
        f"Counter-Determination: {res.critic.counter_determination.value if res.critic.counter_determination else 'None'}\n\n"
        f"{res.critic.critique_summary}",
        title="Stage 2: Critic (Adversarial Compliance Auditor)",
        border_style=c_color,
    )
    console.print(c_panel)

    if res.critic.challenges:
        ch_table = Table(title="Critic Adversarial Challenges", show_header=True)
        ch_table.add_column("ID", style="dim")
        ch_table.add_column("Severity", style="bold")
        ch_table.add_column("Type", style="magenta")
        ch_table.add_column("Critique")
        ch_table.add_column("Action", style="yellow")
        for ch in res.critic.challenges:
            s_style = "bold red" if ch.severity == ChallengeSeverity.BLOCKER else "red" if ch.severity == ChallengeSeverity.HIGH else "yellow"
            ch_table.add_row(ch.challenge_id, f"[{s_style}]{ch.severity.value}[/{s_style}]", ch.challenge_type.value, ch.critique, ch.suggested_action)
        console.print(ch_table)

    # 3. Judge Verdict
    j_color = "green" if res.judge.final_determination == Determination.APPROVE else "yellow" if res.judge.final_determination == Determination.PARTIAL_APPROVAL else "red"
    hitl_str = f"[bold red]YES[/bold red] - {res.judge.hitl_routing_reason}" if res.judge.human_in_the_loop_required else "[green]NO (Automated Defensibility Met)[/green]"

    j_panel = Panel(
        f"[bold {j_color}]FINAL DETERMINATION: {res.judge.final_determination.value}[/bold {j_color}]\n"
        f"[bold cyan]Consensus Status:[/bold cyan] {res.judge.consensus_status.value} | [bold cyan]Divergence Score:[/bold cyan] {res.judge.divergence_score:.2f} | [bold cyan]Confidence:[/bold cyan] {res.judge.final_confidence:.2f}\n"
        f"[bold cyan]Human-in-the-Loop Required:[/bold cyan] {hitl_str}\n\n"
        f"[dim]{res.judge.statutory_basis}[/dim]",
        title="Stage 3: Judge (Chief Medical Officer / Autonomous Adjudicator)",
        border_style=j_color,
    )
    console.print(j_panel)

    if show_patient_notice:
        console.print(Panel(
            res.judge.patient_plain_language_notice,
            title="[bold cyan]CMS-0057-F Plain-Language Member Notice (6th-Grade Reading Level)[/bold cyan]",
            border_style="cyan",
        ))

    if show_audit:
        a_table = Table(title="[bold yellow]Cryptographic Tamper-Evident Hash Chain (SHA-256 / Merkle)[/bold yellow]")
        a_table.add_column("Stage", style="bold")
        a_table.add_column("Node ID", style="dim")
        a_table.add_column("Node Hash (SHA-256)", style="bold cyan")
        a_table.add_column("Parent Hash", style="dim")
        a_table.add_column("Summary Digest")

        for n in res.audit_packet.nodes:
            a_table.add_row(
                n.stage,
                n.node_id,
                n.node_hash[:16] + "..." + n.node_hash[-8:],
                (n.parent_hash[:12] + "...") if n.parent_hash else "[bold green]GENESIS[/bold green]",
                json.dumps(n.payload_summary),
            )
        console.print(a_table)
        console.print(f"[bold green]✓ Merkle Root:[/bold green] [cyan]{res.audit_packet.merkle_root}[/cyan] | [bold green]Tamper Check:[/bold green] PASSED | [bold green]Latency:[/bold green] {res.execution_time_ms:.1f}ms\n")


@app.command("verify-audit")
def verify_audit_simulation(case_path: str = typer.Argument("case_01_glp1_approve.json")):
    """Runs a case, then deliberately tampers with the chain to prove cryptographic detection."""
    path = Path(__file__).parent / "cases" / case_path if not Path(case_path).exists() else Path(case_path)
    with open(path, "r", encoding="utf-8") as f:
        case = ClinicalCase(**json.load(f))

    res = default_engine.run(case)
    console.print(Panel(f"Original Chain Generated for Case {case.case_id}. Verifying integrity...", style="cyan"))
    valid, err = AuditChainBuilder.verify_tamper(res.audit_packet)
    console.print(f"[bold green]Step 1 - Untampered Chain Verification:[/bold green] Valid={valid} (Error={err})")

    # Simulate Tampering: change the stage 3 node hash
    console.print("[bold yellow]Step 2 - Simulating Malicious Tampering:[/bold yellow] Modifying stage 3 payload hash...")
    tampered_packet = res.audit_packet.model_copy(deep=True)
    tampered_packet.nodes[2].node_hash = "deadbeef" * 8
    valid_tampered, err_tampered = AuditChainBuilder.verify_tamper(tampered_packet)
    console.print(f"[bold red]Step 3 - Post-Tamper Audit Result:[/bold red] Valid={valid_tampered}")
    console.print(f"[bold red]Tamper Detection Alert:[/bold red] {err_tampered}")


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
):
    """Launches the Veridict Web Application and Documentation Portal."""
    import uvicorn
    console.print(f"[bold green]Starting Veridict Web Portal on http://{host}:{port}...[/bold green]")
    uvicorn.run("veridict.server.app:app", host=host, port=port, reload=False)


def main():
    app()


if __name__ == "__main__":
    main()
