# ALIP Architecture

**Version:** 0.2.0 (Post-Mentor Review)  
**Status:** Production-Ready Delivery System  
**Last Updated:** 2024-01-02

---

## Core Principle

**ALIP is not a tool. It is a delivery system.**

Every component is designed to produce client-readable, explainable, reproducible outputs.

---

## Architecture Layers

### 1. Engagement Lifecycle (State Machine)

```
NEW → INGESTED → ANALYZED → REVIEWED → FINALIZED
```

**Enforcement:**
- CLI blocks invalid state transitions
- Each transition requires specific artifacts
- State changes are logged with timestamps

**Implementation:** `core/state_machine.py`

---

### 2. Data Layer (Skills)

**Philosophy:** Deterministic first, LLM second

Skills are pure functions that:
- Take explicit inputs
- Produce `SkillOutput` with confidence & sources
- Have no side effects
- Are fully testable

**Structure:**
```python
@skill_wrapper("scan_repo")
def scan_repo(path: Path) -> SkillOutput:
    # Deterministic parsing
    inventory = {...}
    
    return SkillOutput(
        skill_name="scan_repo",
        data=inventory,
        confidence=ConfidenceLevel.HIGH,
        sources=[SourceReference(...)],
        metadata={"total_files": 100}
    )
```

**Location:** `skills/`

---

### 3. Analysis Layer (Agents)

Agents orchestrate skills to produce artifacts:

| Agent | Input | Output | State Transition |
|-------|-------|--------|------------------|
| **IngestionAgent** | Raw files | Normalized artifacts | NEW → INGESTED |
| **TopologyAgent** | Artifacts | Dependency graph | INGESTED → ANALYZED |
| **CostAnalysisAgent** | Artifacts + Graph | Cost drivers | |
| **RiskAnalysisAgent** | Artifacts + Graph | Risk register | |
| **SynthesisAgent** | All artifacts | Executive summary | ANALYZED → FINALIZED |

**Location:** `agents/`

---

### 4. Human-in-the-Loop (Review Gate)

Every artifact goes through review:

```python
gate = ReviewGate(workspace)

# Submit artifact
gate.submit_for_review(artifact, artifact_path)

# Human reviews and decides
gate.approve(artifact_id, reviewer="John Doe")
# or
gate.reject(artifact_id, reviewer="John Doe", reason="Incomplete data")
# or
gate.request_changes(artifact_id, changes=["Add more sources"])
```

**Enforcement:**
- ANALYZED → REVIEWED transition blocked until approval
- Review decisions are logged
- Audit trail maintained

**Location:** `core/review_gate.py`

---

### 5. LLM Layer (Prompts)

**Versioned prompts** in `prompts/`:
```
prompts/
├── topology/
│   └── system_prompt_v1.md
├── cost_analysis/
│   └── system_prompt_v1.md
├── risk_analysis/
│   └── system_prompt_v1.md
└── synthesis/
    └── system_prompt_v1.md
```

**Rules:**
1. Every prompt is versioned (v1.md, v2.md)
2. Changes are documented in version history
3. Old versions are never deleted (for reproducibility)
4. Prompts include output schema + examples

---

## Safety Guarantees

### 1. Read-Only Enforcement

**CLI Level:**
```python
if not config.read_only_mode:
    console.print("Security Error: Read-only mode disabled")
    sys.exit(1)
```

**Skill Level:**
- No write operations in any skill
- Database connections are SELECT-only
- Repository access is clone/read-only

### 2. State Machine Enforcement

**Prevents:**
- Skipping ingestion
- Analyzing without data
- Finalizing without review
- Running out of order

**Implementation:**
```python
validate_transition(
    current=EngagementState.NEW,
    target=EngagementState.FINALIZED  # Raises StateViolationError
)
```

### 3. Traceability

Every output includes:
- `sources`: List of source references (file, line, timestamp)
- `confidence`: HIGH | MEDIUM | LOW
- `metadata`: Context-specific data
- `timestamp`: When artifact was created

---

## Artifact Schema

**Standard Format:**
```json
{
  "artifact_type": "repo_inventory",
  "engagement_id": "client-2024-001",
  "created_at": "2024-01-02T10:00:00",
  "review_status": "pending",
  "confidence": "high",
  "data": {...},
  "sources": [
    {
      "type": "repo",
      "path": "/src/main.py",
      "line_number": 42,
      "snippet": "def process_order(...)",
      "timestamp": "2024-01-02T10:00:00"
    }
  ],
  "metrics": {
    "total_files": 1247,
    "total_lines": 125000
  }
}
```

---

## Testing Strategy

### Unit Tests
- Every skill has unit tests
- Mock external dependencies
- Assert deterministic outputs

### Integration Tests
- Full workflow (NEW → FINALIZED)
- Artifact completeness
- JSON schema validity
- No network calls
- Deterministic outputs

### E2E Test
```bash
pytest tests/integration/test_e2e_workflow.py -v
```

Validates:
- State transitions
- Read-only enforcement
- Artifact generation
- Source traceability
- Review gate workflow

---

## Delivery Model

### Phase 1: Project-Based (Current)
1. Client provides: repo, DB exports, docs, query logs
2. ALIP ingests → analyzes → generates artifacts
3. Human reviews artifacts
4. Final deliverables approved
5. Client receives: PDF reports + raw artifacts

### Phase 2: Continuous Monitoring (Future)
1. ALIP runs weekly on production exports
2. Tracks changes over time
3. Alerts on new risks
4. Trend analysis

---

## Key Design Decisions

### 1. Why State Machine?

**Problem:** Clients running analysis before ingestion, or skipping review  
**Solution:** Explicit lifecycle with validation  
**Benefit:** Trust, reproducibility, audit trail

### 2. Why Skill Wrappers?

**Problem:** Inconsistent outputs, no confidence scoring  
**Solution:** Standard `SkillOutput` wrapper  
**Benefit:** Every output has metadata + sources

### 3. Why Review Gates?

**Problem:** AI outputs going directly to clients  
**Solution:** Human approval required  
**Benefit:** Trust, quality control, legal safety

### 4. Why Versioned Prompts?

**Problem:** Changing prompts breaks reproducibility  
**Solution:** Version every prompt, never delete old ones  
**Benefit:** Can reproduce any past analysis exactly

---

## Scaling Considerations

### Single Engagement (Current)
- Local execution
- Manual CLI commands
- Human review via file inspection

### Multiple Engagements (Phase 2)
- Parallel processing
- Automated scheduling
- Review dashboard UI

### Enterprise Scale (Phase 3)
- API server
- Multi-tenancy
- Role-based access control
- Automated approvals (with human oversight)

---

## Comparison: Tool vs. Delivery System

| Aspect | Tool (v0.1) | Delivery System (v0.2) |
|--------|-------------|------------------------|
| **State** | Implicit | Explicit state machine |
| **Safety** | Documented | Enforced |
| **Outputs** | JSON files | Reviewed artifacts |
| **Confidence** | Missing | Always included |
| **Sources** | Optional | Always included |
| **Review** | Manual | Gated workflow |
| **Reproducibility** | Hoped for | Guaranteed |

---

## Next Steps (Roadmap)

### Phase 2 (Q1 2024)
- [ ] Implement remaining agents (Topology, Cost, Risk, Synthesis)
- [ ] PDF report generation
- [ ] Review dashboard UI
- [ ] Continuous monitoring mode

### Phase 3 (Q2 2024)
- [ ] API server
- [ ] Multi-tenant architecture
- [ ] Automated scheduling
- [ ] Change impact simulation

---

## References

- [State Machine](core/state_machine.py)
- [Skill Output](core/skill_output.py)
- [Review Gate](core/review_gate.py)
- [E2E Tests](tests/integration/test_e2e_workflow.py)

---

**This is a delivery system, not a developer utility.**

Every line of code serves client trust, safety, and explainability.
