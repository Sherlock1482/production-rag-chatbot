# SDD Constitution — Talent Acquisition Agentic RAG Platform

## 1. Purpose & Scope
This constitution defines the non-negotiable engineering principles and Spec-Driven Development (SDD) standards for the **Talent Acquisition (TA) Copilot & Agentic Interview Platform**. Every new agent workflow, retrieval strategy, tool, or API endpoint must strictly adhere to these principles.

---

## 2. Core Engineering Principles

### Principle 1: Specification Before Implementation (Spec-First)
No application logic, prompt templates, or API routes may be written without an approved specification in `specs/`. Each specification must define:
1. **Problem Statement & Scope**
2. **Strict Typed Contracts (Pydantic models / TypeScript interfaces)**
3. **Prompt Specification & Boundary Rules**
4. **Acceptance Criteria (BDD Given-When-Then scenarios)**
5. **Automated Test Plan**

### Principle 2: Strict Typed Data Contracts
All agentic workflows that produce structured data (fit reports, comparison tables, scorecards, email drafts) must use Pydantic `BaseModel` schemas with type hints, field descriptions, and range validations. Free-form, unstructured markdown is prohibited for core workflow outputs where structured UI components or downstream tools depend on the data.

### Principle 3: Evidence Grounding & Zero Hallucination Invariant
1. Candidate skills, experience years, and employment history must be grounded in verbatim or semantically verified evidence from retrieved document chunks (Qdrant) or authoritative interview records (`ta_interviews.db` / Google Calendar).
2. If evidence for a required qualification is missing, the agent **must explicitly flag it as missing or unverified**, never infer or assume candidate capability to satisfy a requested quota.

### Principle 4: Deterministic Tools & Safe MCP Protocols
1. Tools exposed via FastMCP (`backend/mcp_server.py`) must have deterministic parameter schemas and fail-safe error handling.
2. Tool responses must return structured JSON payloads with explicit `success` or `found` booleans, human-readable error messages, and raw status indicators.

### Principle 5: Human-in-the-Loop (HITL) for Outbound Actions
Any destructive or external-facing action (e.g., sending real emails to candidates, deleting records, rescheduling confirmed interviews) must follow a two-phase protocol:
- **Phase 1 (Draft/Preview)**: Agent generates structured action preview for the recruiter.
- **Phase 2 (Confirmation/Execution)**: Explicit recruiter confirmation is required before the tool executes the outbound network request.

### Principle 6: Test-First Acceptance Gates
Every feature must have automated unit and integration tests under `tests/` before it is wired into `backend/main.py`. A feature is only considered done when:
1. Schema parsing and validation pass with 100% type conformance.
2. Synthetic edge-case tests pass (missing data, conflicting data, out-of-scope inputs).
3. Guardrails (input, evidence, output) successfully trigger on adversarial or out-of-domain queries.

### Principle 7: Continuous Observability & Tracing
Every agentic decision, retrieval query, tool execution, and LLM generation must be recorded with Langfuse spans and metadata (`session_id`, `intent`, `model`, latency, token counts). Silent failures or untraced LLM calls are prohibited.

---

## 3. SDD Workflow Lifecycle

```
┌─────────────────────────────────┐
│ 1. SPECIFICATION (specs/)       │
│    - spec.md                    │
│    - test_plan.md               │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 2. TEST HARNESS (tests/)        │
│    - Unit tests with mock data  │
│    - Failing baseline tests     │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 3. CORE UTILITY (backend/utils/)│
│    - Pydantic models            │
│    - LLM structured output      │
│    - FastMCP tools (if action)  │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 4. INTEGRATION (backend/main.py)│
│    - Intent detector update     │
│    - Streaming/REST routing     │
│    - Langfuse tracing           │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 5. UI & CLIENT (frontend/app/)  │
│    - TypeScript contract match  │
│    - Interactive components     │
└─────────────────────────────────┘
```
