# Vinyl Collection Agent
# Requirements Specification (IREB-aligned, English)

---

## 1. System Goal

The system provides an agent-based solution for cataloguing, valuating,
and documenting a private vinyl record collection.

At the core of the system is an AI agent orchestrated via LangGraph.
The agent coordinates specialized tools for image analysis, metadata lookup,
pressing identification, valuation, and insurance-grade documentation.

The system is designed according to an **Agentic-First** paradigm:
the agent is the primary decision-maker; backend services are infrastructure.

---

## 2. Stakeholders

- Primary user: Vinyl collector / collection owner
- Secondary stakeholders:
  - Insurance companies (documentation and valuation)
  - Archivists / auditors (traceability and evidence)

---

## 3. System Context

- Mobile Progressive Web App (PWA) for capture and review
- Backend API (FastAPI) for orchestration, persistence, and exports
- AI Agent (LangGraph) for decision workflows
- External data sources:
  - Discogs
  - MusicBrainz
  - Web-based price sources (where legally permitted)

---

## 4. Functional Requirements

### FR-01 Capture (Mobile-First)

The system MUST allow the user to capture vinyl records using a smartphone camera.

Supported media types:
- Front cover
- Spine (mandatory for non-barcode items)
- Back cover
- Label (optional)
- Runout / matrix (optional, on demand)
- Barcode (optional)

Captured media MUST be uploaded directly to the backend and linked to a capture session.

---

### FR-02 Agentic Intake & Feature Extraction

The AI agent MUST:
- Extract textual and visual features from uploaded media
- Detect barcodes where present
- Normalize extracted metadata (artist names, labels, catalog numbers)
- Persist extracted features as evidence artifacts

No business logic SHALL be embedded in prompts.
All extraction MUST be implemented via tools.

---

### FR-03 Pressing Identification & Decision Gate

The AI agent MUST:
- Identify multiple candidate releases/pressings
- Compute a confidence score per candidate
- Store structured evidence for each candidate

Decision rules:
- Confidence ≥ 0.85 → automatic commit
- Confidence < 0.85 → review required

The agent MUST generate review tasks if:
- Required media is missing
- Confidence threshold is not met
- Conflicting metadata exists

---

## 5. Valuation Agent (Extension)

### FR-04 Market Valuation

The Valuation Agent MUST determine a **market value range** for each confirmed pressing.

Market valuation MUST:
- Be based on recent sales and/or listings
- Use robust statistics (median, IQR, min/max)
- Explicitly store currency and timestamp
- Record all sources as evidence

The agent MUST NOT invent prices or extrapolate without source data.

---

### FR-05 Replacement (Insurance) Valuation

The Valuation Agent MUST compute a **replacement value** suitable for insurance purposes.

Replacement valuation MUST:
- Be derived from market valuation
- Account for:
  - Availability / rarity
  - Pressing specificity
  - Replacement difficulty
- Be conservative and defensible

Each replacement valuation MUST include:
- Valuation method
- Assumptions
- Confidence level

---

### FR-06 Valuation Traceability

All valuations MUST be:
- Time-series capable (historical tracking)
- Reproducible
- Linked to raw evidence snapshots

---

## 6. PDF & Insurance Documentation Tool (Extension)

### FR-07 Insurance Report Generation

The system MUST generate an insurance-grade PDF document.

The PDF MUST include:
- Collection metadata (owner, date, version)
- Itemized list of records:
  - Artist
  - Title
  - Confirmed pressing
  - Condition
  - Market value range
  - Replacement value
- Aggregated totals by value class
- Embedded photo evidence per item

---

### FR-08 PDF Quality & Compliance

The PDF MUST:
- Use a stable layout (DIN A4)
- Be suitable for long-term archival
- Clearly separate market value and replacement value
- Include disclaimers and valuation methodology

The PDF MUST be reproducible from stored data without re-running the agent.

---

## 7. Non-Functional Requirements

### NFR-01 Transparency & Evidence

Every agent decision MUST be backed by:
- Evidence objects
- Source references
- Timestamps

Black-box decisions are NOT permitted.

---

### NFR-02 Determinism & Reproducibility

Agent workflows MUST be deterministic given identical inputs.
Re-running an agent with the same data MUST yield identical results.

---

### NFR-03 Extensibility

The system MUST allow:
- Addition of new valuation sources
- Addition of new document formats
- Modification of confidence thresholds

without changes to existing agent logic.

---

### NFR-04 Legal & Ethical Constraints

Scraping MUST:
- Respect robots.txt
- Respect terms of service
- Be rate-limited and auditable

The system MUST fall back gracefully if sources are unavailable.

---

## 8. System Boundaries

Out of scope for the MVP:
- Marketplace or selling functionality
- Social or sharing features
- Automated trading or pricing advice

---

## 9. Architectural Principle (Normative)

> The AI agent is the system.
> APIs, databases, and UIs are supporting components.

All core business decisions MUST be implemented as agent workflows.
