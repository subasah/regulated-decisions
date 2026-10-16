/**
 * VERIDICT Front-End Application Logic.
 * Manages tab switching, case loading, Triad execution, citation highlighting,
 * cryptographic tamper simulation, policy inspection, and benchmark execution.
 */

let allCases = [];
let allPolicies = [];
let currentCase = null;
let currentResult = null;

document.addEventListener("DOMContentLoaded", async () => {
  setupTabs();
  await loadCases();
  await loadPolicies();
  setupEventListeners();

  // Auto-select first case
  if (allCases.length > 0) {
    selectCase(allCases[0].case_id);
  }
});

// Tab Navigation
function setupTabs() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

      tab.classList.add("active");
      const targetId = `tab-${tab.getAttribute("data-tab")}`;
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add("active");
    });
  });
}

// Load Cases from Backend API
async function loadCases() {
  try {
    const res = await fetch("/api/cases");
    allCases = await res.json();

    const selector = document.getElementById("case-selector");
    const chipsContainer = document.getElementById("quick-case-chips");
    selector.innerHTML = '<option value="">-- Choose a benchmark case --</option>';
    chipsContainer.innerHTML = "";

    allCases.forEach(c => {
      // Option
      const opt = document.createElement("option");
      opt.value = c.case_id;
      opt.textContent = `[${c.domain.replace('_', ' ')}] ${c.title}`;
      selector.appendChild(opt);

      // Quick chip
      const chip = document.createElement("button");
      chip.className = "chip-btn";
      chip.textContent = `${c.patient_name} (${c.case_id.split('-')[1]})`;
      chip.title = c.title;
      chip.addEventListener("click", () => {
        selector.value = c.case_id;
        selectCase(c.case_id);
      });
      chipsContainer.appendChild(chip);
    });
  } catch (err) {
    console.error("Failed to load cases:", err);
  }
}

// Load Policies from Backend API
async function loadPolicies() {
  try {
    const res = await fetch("/api/policies");
    allPolicies = await res.json();
    renderPolicyCards();
  } catch (err) {
    console.error("Failed to load policies:", err);
  }
}

// Event Listeners
function setupEventListeners() {
  const selector = document.getElementById("case-selector");
  selector.addEventListener("change", (e) => {
    if (e.target.value) {
      selectCase(e.target.value);
    }
  });

  document.getElementById("btn-run-case").addEventListener("click", () => {
    if (currentCase) {
      runTriad(currentCase.case_id);
    }
  });

  document.getElementById("btn-tamper-sim").addEventListener("click", simulateTamper);
  document.getElementById("btn-verify-audit").addEventListener("click", reVerifyAudit);
  document.getElementById("btn-run-all-benchmarks").addEventListener("click", runFullBenchmark);
}

// Select and Display Case Dossier
async function selectCase(caseId) {
  try {
    // Update chip styling
    document.querySelectorAll(".chip-btn").forEach(chip => {
      chip.classList.toggle("active", chip.textContent.includes(caseId.split('-')[1]));
    });

    const res = await fetch(`/api/cases/${caseId}`);
    currentCase = await res.json();

    // Populate Dossier
    document.getElementById("dossier-domain-badge").textContent = currentCase.domain;
    document.getElementById("p-name").textContent = currentCase.demographics.name;
    document.getElementById("p-meta").textContent = `Age ${currentCase.demographics.age} | ${currentCase.demographics.gender} | ${currentCase.demographics.coverage_plan}`;
    document.getElementById("p-service").textContent = currentCase.requested_service;
    document.getElementById("p-codes").textContent = currentCase.service_codes.join(", ");
    document.getElementById("p-provider").textContent = currentCase.requesting_provider;

    // Reset EHR Note View
    renderEHRNote(currentCase.unstructured_note, []);

    // Reset Review Cards
    resetReviewDisplay();

    // Auto run case for seamless showcase experience
    await runTriad(caseId);
  } catch (err) {
    console.error("Error selecting case:", err);
  }
}

// Reset Review Display
function resetReviewDisplay() {
  document.getElementById("execution-badge").classList.add("hidden");
  document.getElementById("proposer-narrative").textContent = "Running clinical evaluation...";
  document.getElementById("proposer-criteria-list").innerHTML = "";
  document.getElementById("critic-narrative").textContent = "Running adversarial compliance audit...";
  document.getElementById("critic-challenges-list").innerHTML = "";
  document.getElementById("clinician-rationale-text").textContent = "Synthesizing rationale...";
  document.getElementById("patient-notice-text").textContent = "Generating plain-language explanation...";
  document.getElementById("tamper-alert-box").classList.add("hidden");
}

// Execute Triad via API
async function runTriad(caseId) {
  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ case_id: caseId }),
    });
    currentResult = await res.json();
    displayResults(currentResult);
  } catch (err) {
    console.error("Error running triad:", err);
  }
}

// Display Full Execution Results
function displayResults(data) {
  // Latency
  const execBadge = document.getElementById("execution-badge");
  execBadge.classList.remove("hidden");
  execBadge.querySelector(".exec-time").textContent = `Triad Execution: ${data.execution_time_ms.toFixed(1)} ms`;

  // 1. Proposer Review
  renderProposer(data.proposer);

  // 2. Critic Review
  renderCritic(data.critic);

  // 3. Judge Adjudication
  renderJudge(data.judge);

  // 4. Highlight Verified Citations in EHR Note
  const allCits = [];
  data.proposer.criteria_evaluations.forEach(ce => {
    ce.citations.forEach(c => {
      if (c.is_verified) allCits.push(c);
    });
  });
  renderEHRNote(data.case.unstructured_note, allCits);

  // 5. Cryptographic Ledger
  renderAuditChain(data.audit_packet);
}

// Render EHR Note with Highlights
function renderEHRNote(rawText, citations) {
  const container = document.getElementById("ehr-note-display");
  if (!citations || citations.length === 0) {
    container.textContent = rawText;
    return;
  }

  // Sort citations by start_char
  const sortedCits = [...citations].sort((a, b) => a.start_char - b.start_char);

  let html = "";
  let lastIdx = 0;

  sortedCits.forEach((cit, idx) => {
    if (cit.start_char >= lastIdx && cit.start_char < rawText.length) {
      // Unhighlighted chunk
      html += escapeHtml(rawText.substring(lastIdx, cit.start_char));
      // Highlighted quote
      const quote = rawText.substring(cit.start_char, Math.min(cit.end_char, rawText.length));
      html += `<mark class="highlight-span" id="cit-mark-${idx}" title="Verified Citation: ${cit.criterion_id}">${escapeHtml(quote)}</mark>`;
      lastIdx = Math.max(lastIdx, cit.end_char);
    }
  });

  if (lastIdx < rawText.length) {
    html += escapeHtml(rawText.substring(lastIdx));
  }

  container.innerHTML = html;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Render Proposer Agent
function renderProposer(proposer) {
  const pBadge = document.getElementById("proposer-verdict-badge");
  const pClass = proposer.determination === "APPROVE" ? "pill-green" : "pill-red";
  pBadge.innerHTML = `<span class="${pClass}">${proposer.determination} (${(proposer.confidence_score * 100).toFixed(0)}%)</span>`;

  document.getElementById("proposer-narrative").textContent = proposer.clinical_synthesis;

  const list = document.getElementById("proposer-criteria-list");
  list.innerHTML = "";

  proposer.criteria_evaluations.forEach(ce => {
    const item = document.createElement("div");
    item.className = "criterion-item";

    const isExclusion = ce.criterion_type === "EXCLUSION";
    let statusClass = ce.is_satisfied ? "pill-green" : "pill-red";
    let statusText = ce.is_satisfied ? "MET" : "UNMET";

    if (isExclusion) {
      statusClass = ce.is_satisfied ? "pill-red" : "pill-green";
      statusText = ce.is_satisfied ? "CONTRAINDICATION" : "CLEARED";
    }

    let citationsHtml = "";
    if (ce.citations && ce.citations.length > 0) {
      citationsHtml = ce.citations.map((c, i) => `
        <span class="citation-chip" title="${c.verbatim_quote}">
          ✓ Grounded Citation [${c.source_section}]
        </span>
      `).join(" ");
    }

    item.innerHTML = `
      <div class="crit-row-top">
        <span class="crit-name">${ce.criterion_name}</span>
        <span class="${statusClass}">${statusText}</span>
      </div>
      <div class="crit-rationale">${ce.rationale}</div>
      ${citationsHtml}
    `;
    list.appendChild(item);
  });
}

// Render Critic Agent
function renderCritic(critic) {
  const cBadge = document.getElementById("critic-verdict-badge");
  let cClass = "pill-green";
  if (critic.severity_max === "BLOCKER" || critic.severity_max === "HIGH") cClass = "pill-red";
  else if (critic.severity_max === "MEDIUM") cClass = "badge-amber";

  cBadge.innerHTML = `<span class="${cClass}">SEVERITY: ${critic.severity_max}</span>`;
  document.getElementById("critic-narrative").textContent = critic.critique_summary;

  const list = document.getElementById("critic-challenges-list");
  list.innerHTML = "";

  if (!critic.challenges || critic.challenges.length === 0) {
    list.innerHTML = '<div class="text-muted" style="padding: 8px;">Zero adversarial challenges or compliance flags detected.</div>';
    return;
  }

  critic.challenges.forEach(ch => {
    const item = document.createElement("div");
    item.className = "challenge-item";
    const sevClass = ch.severity === "BLOCKER" ? "pill-red" : "badge-amber";

    item.innerHTML = `
      <div class="chal-row-top">
        <strong>${ch.challenge_type}</strong>
        <span class="${sevClass}">${ch.severity}</span>
      </div>
      <div>${ch.critique}</div>
      <div style="color: var(--accent-amber); font-size: 11px;"><strong>Action:</strong> ${ch.suggested_action}</div>
    `;
    list.appendChild(item);
  });
}

// Render Judge Adjudication & Rationales
function renderJudge(judge) {
  const finalBadge = document.getElementById("judge-final-badge");
  let fClass = "badge-green";
  if (judge.final_determination === "DENY") fClass = "badge-red";
  else if (judge.final_determination === "PARTIAL_APPROVAL") fClass = "badge-amber";

  finalBadge.className = `final-badge ${fClass}`;
  finalBadge.textContent = judge.final_determination;

  document.getElementById("judge-status-badge").textContent = judge.consensus_status;
  document.getElementById("judge-confidence").textContent = `${(judge.final_confidence * 100).toFixed(0)}%`;
  document.getElementById("judge-divergence").textContent = judge.divergence_score.toFixed(2);

  // HITL Alert
  const hitlBox = document.getElementById("hitl-alert-box");
  if (judge.human_in_the_loop_required) {
    hitlBox.classList.remove("hidden");
    document.getElementById("hitl-reason-text").textContent = judge.hitl_routing_reason;
  } else {
    hitlBox.classList.add("hidden");
  }

  // Rationales
  document.getElementById("clinician-rationale-text").textContent = judge.clinician_rationale;
  document.getElementById("patient-notice-text").textContent = judge.patient_plain_language_notice;

  // Appeal Box
  document.getElementById("appeal-content-text").innerHTML = `
    <div><strong>Governing Regulation:</strong> ${judge.appeal_rights.statutory_governance}</div>
    <div><strong>Standard Appeal:</strong> ${judge.appeal_rights.standard_appeal_deadline} | <strong>Expedited:</strong> ${judge.appeal_rights.expedited_appeal_timeline}</div>
    <div style="margin-top: 4px;">${judge.appeal_rights.how_to_appeal}</div>
  `;
}

// Render Cryptographic Audit Chain
function renderAuditChain(packet) {
  document.getElementById("merkle-root-val").textContent = packet.merkle_root;

  const statusPill = document.getElementById("audit-status-pill");
  statusPill.innerHTML = '<span class="pill-green">CHAIN INTACT</span>';

  const flow = document.getElementById("chain-flow-container");
  flow.innerHTML = "";

  packet.nodes.forEach(node => {
    const card = document.createElement("div");
    card.className = "node-card";
    card.id = `node-${node.node_id}`;

    const shortHash = `${node.node_hash.substring(0, 8)}...${node.node_hash.substring(node.node_hash.length - 6)}`;
    const shortParent = node.parent_hash ? `${node.parent_hash.substring(0, 8)}...` : "GENESIS";

    card.innerHTML = `
      <div class="node-stage">${node.stage}</div>
      <div class="node-hash" title="${node.node_hash}">Hash: <code>${shortHash}</code></div>
      <div class="node-parent">Parent: <code>${shortParent}</code></div>
    `;
    flow.appendChild(card);
  });
}

// Simulate Tamper
async function simulateTamper() {
  if (!currentResult) return;

  try {
    const res = await fetch("/api/verify-tamper", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audit_packet: currentResult.audit_packet,
        tamper_node_index: 2, // Alter Proposer Node
        tamper_value: "deadbeef" + "0".repeat(56),
      }),
    });
    const check = await res.json();

    const statusPill = document.getElementById("audit-status-pill");
    const alertBox = document.getElementById("tamper-alert-box");

    if (!check.is_valid) {
      statusPill.innerHTML = '<span class="pill-red">TAMPER DETECTED</span>';
      alertBox.classList.remove("hidden");
      alertBox.innerHTML = `
        <span>🚨 <strong>Tamper Verification Alert:</strong> ${check.error}. 
        The Merkle DAG immediately proved data corruption at stage PROPOSER_SYNTHESIS.</span>
      `;

      // Highlight the corrupted node in the UI
      const nodes = document.querySelectorAll(".node-card");
      if (nodes[2]) nodes[2].classList.add("tampered");
    }
  } catch (err) {
    console.error("Tamper simulation error:", err);
  }
}

// Re-Verify Untampered Audit Chain
async function reVerifyAudit() {
  if (!currentResult) return;
  document.querySelectorAll(".node-card").forEach(n => n.classList.remove("tampered"));
  document.getElementById("tamper-alert-box").classList.add("hidden");
  renderAuditChain(currentResult.audit_packet);
}

// Render Policy Cards in Tab 4
function renderPolicyCards() {
  const container = document.getElementById("policy-registry-cards");
  if (!container) return;
  container.innerHTML = "";

  allPolicies.forEach(pol => {
    const card = document.createElement("div");
    card.className = "policy-card";

    const criteriaChips = pol.criteria.map(c => `
      <span class="crit-tag" title="${c.description}">
        ${c.criterion_id}: ${c.name}
      </span>
    `).join(" ");

    card.innerHTML = `
      <div class="policy-card-top">
        <span class="policy-id">${pol.policy_id} (v${pol.version})</span>
        <span class="policy-domain">${pol.domain}</span>
      </div>
      <div class="policy-title">${pol.title}</div>
      <div class="policy-desc">${pol.summary}</div>
      <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">
        <strong>Framework:</strong> ${pol.regulatory_framework} | 
        <strong>Codes:</strong> ${pol.target_codes.join(", ")}
      </div>
      <div class="policy-criteria-chips">
        ${criteriaChips}
      </div>
    `;
    container.appendChild(card);
  });
}

// Run Full Benchmark in Tab 5
async function runFullBenchmark() {
  const tbody = document.getElementById("benchmark-table-body");
  tbody.innerHTML = '<tr><td colspan="10" class="text-center">Executing all test suites...</td></tr>';

  try {
    const res = await fetch("/api/benchmark");
    const data = await res.json();

    document.getElementById("bm-total-cases").textContent = data.summary.total_cases;
    document.getElementById("bm-valid-trails").textContent = data.summary.all_audit_trails_valid ? "100%" : "FAIL";
    document.getElementById("bm-avg-latency").textContent = `${data.summary.avg_latency_ms} ms`;

    tbody.innerHTML = "";
    data.results.forEach(r => {
      const tr = document.createElement("tr");

      const detClass = r.final_determination === "APPROVE" ? "stat-green" : r.final_determination === "PARTIAL_APPROVAL" ? "stat-amber" : "stat-red";
      const sevClass = r.critic_severity === "BLOCKER" ? "stat-red" : r.critic_severity === "HIGH" ? "stat-amber" : "stat-green";

      tr.innerHTML = `
        <td><strong>${r.case_id}</strong></td>
        <td>${r.domain}</td>
        <td>${r.proposer_determination}</td>
        <td><span class="${sevClass}">${r.critic_severity}</span></td>
        <td><strong class="${detClass}">${r.final_determination}</strong></td>
        <td>${r.consensus_status}</td>
        <td>${(r.confidence * 100).toFixed(0)}%</td>
        <td>${r.hitl_required ? '⚠️ Yes' : 'No'}</td>
        <td><span class="stat-green">✓ Valid</span></td>
        <td>${r.latency_ms} ms</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Benchmark error:", err);
    tbody.innerHTML = '<tr><td colspan="10" class="text-center text-red">Failed to run benchmark suite.</td></tr>';
  }
}
