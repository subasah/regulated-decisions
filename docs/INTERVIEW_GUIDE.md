# Recruiter & Technical Interview Playbook: Presenting VERIDICT

This guide equips you to present **VERIDICT** in technical interviews, product architecture discussions, and recruiter conversations across top-tier health-tech, AI engineering, and enterprise platforms (e.g., Epic, Optum, Cohere Health, Oscar, Flatiron, Tempus, Google Health, Palantir, Anthropic, OpenAI).

---

## 1. The 30-Second Elevator Pitch

> *"Most generative AI demos fail in healthcare because black-box LLMs hallucinate citations and miss life-threatening contraindications—which violates federal regulations like CMS-0057-F and ERISA § 503. I built **VERIDICT**, an open-architecture decision intelligence engine for regulated healthcare. It uses an adversarial Proposer-Critic-Judge triad grounded in computable clinical policies, enforces zero-tolerance citation verification against raw EHR records, and anchors every decision to an immutable SHA-256 Merkle hash chain for tamper-evident auditing. Across Prior Authorization, Utilization Review, Claims Integrity, and Care Management, it executes in under 5 milliseconds with 100% deterministic safety overrides."*

---

## 2. Key Questions Recruiters & Interviewers Will Ask

### Q1: "Why can't you just use an LLM with a good prompt like 'You are a medical director, follow these rules'?"
**Your Answer:**
- **Probabilistic Drift & Hallucination:** Even with zero temperature, LLMs can fabricate spans, conflate similar lab tests (e.g. Troponin I vs T), or drop edge-case constraints under context pressure.
- **Evidentiary Legal Standards:** Under federal law (CMS-0057-F, ACA § 2719), an adverse determination cannot cite an LLM hallucination. Every denial must point to exact, verifiable character offsets in the patient record.
- **Adversarial Safety Separation:** In clinical medicine, proposing care and auditing care require conflicting incentives. By separating the **Proposer** (advocating for criteria fulfillment) from the **Critic** (adversarially seeking missing contraindications or step-therapy deficits), we prevent the cognitive confirmation bias inherent in a single LLM generation pass.

### Q2: "How does the engine achieve deterministic safety if you are using multi-agent reasoning?"
**Your Answer:**
- "We separate **computable rule logic** from **semantic clinical interpretation**. 
- The criteria engine evaluates boolean predicates ($x \ge \text{threshold}$, $\text{lookback} \le 90\text{ days}$) deterministically using an AST model.
- Furthermore, we enforce a **Hard Safety Override Contract**: If the Critic flags a `BLOCKER` severity challenge (e.g., an FDA Boxed Warning contraindication like family history of Medullary Thyroid Carcinoma in GLP-1 therapy), the Judge mathematically overrules any approval proposal, enforcing denial and routing the case to a licensed Medical Director for mandatory human signoff."

### Q3: "What is the role of the cryptographic audit chain (Merkle DAG)?"
**Your Answer:**
- "Healthcare decisions are subject to retrospective audits, OIG investigations, and legal appeals years after the fact.
- If an insurer or provider modifies the clinical note, alters the criteria evaluation, or changes the denial rationale ex post facto, traditional databases often fail to prove historical state integrity.
- In VERIDICT, every run creates a 5-stage sequential SHA-256 hash chain where each node hashes its canonical JSON payload combined with the previous stage's hash:
  $$H(\text{Node}_i) = \text{SHA256}(\text{CanonicalJSON}(P_i) \parallel H(\text{Node}_{i-1}))$$
- We then compute a Merkle root over the entire trajectory. If an attacker or corrupt database modifies even a single character in the input EHR or proposer findings, the hash chain breaks and our tamper detection algorithm pinpoints the exact point of corruption."

### Q4: "How does this system support Human-in-the-Loop (HITL) without slowing down all clinical operations?"
**Your Answer:**
- "Under CMS-0057-F and NCQA standards, routine approvals that meet 100% of criteria with zero critic challenges can be processed autonomously to eliminate administrative delay for patients.
- However, we define strict statutory triggers for human physician triage:
  1. Any adverse benefit determination (denial).
  2. Any case triggering a deterministic safety override.
  3. Cases where the Proposer and Critic exhibit high divergence ($D > 0.40$).
  4. Clinical scenarios requiring Peer-to-Peer consultation with the requesting physician."

---

## 3. Highlighting the 4 Regulated Verticals

When speaking to interviewers, tailor your examples to their domain:
1. **Payer / Prior Authorization:** Cite the **GLP-1 Wegovy** case (BMI thresholds + lifestyle trial + MTC boxed warning) and **Humira RA** case (12-week step-therapy failure + TB screening).
2. **Hospital / Health System UM:** Cite the **Two-Midnight Rule (CMS-1599-F)** case adjudicating Acute Inpatient (Part A) vs. Outpatient Observation (Part B) for uncomplicated chest pain based on serial troponins and length of stay.
3. **Claims Integrity / Payment Accuracy:** Cite the **Modifier 25** audit case detecting unbundled E/M documentation on joint injections under CMS Claims Manual Ch. 12 § 30.6.6.
4. **Value-Based Care / Population Health:** Cite the **Heart Failure TOC** case stratifying post-discharge high-risk readmissions using the LACE index and SDOH vulnerabilities.

---

## 4. Architectural Tradeoffs & Engineering Decisions

| Architecture Decision | Chosen Approach | Alternative Considered | Engineering Rationale |
| :--- | :--- | :--- | :--- |
| **Criteria Representation** | Computable Pydantic AST JSON Models | Unstructured Natural Language Prompts | Guarantees deterministic predicate evaluation ($\ge, \le, ==$) and schema validation across versions. |
| **Adversarial Triad** | Proposer / Critic / Judge Split | Single LLM with Chain-of-Thought | Prevents confirmation bias; allows independent tuning of auditor severity thresholds. |
| **Grounding Verification** | Exact Character Offset & Span Matching | Semantic Cosine Similarity | Legal compliance (CMS-0057-F) requires verbatim quotes; cosine similarity permits subtle semantic drift. |
| **Audit Ledger** | SHA-256 Sequential Hash Chain + Merkle Tree | Relational SQL Transaction Log | Cryptographically proves non-repudiation and tamper-evidence across distributed payer/provider nodes. |
| **Dual Rationales** | Technical MD Rationale + 6th-Grade Patient Notice | Single Generic Summary | Meets both ERISA § 503 clinical disclosure standards and CMS readability requirements. |
