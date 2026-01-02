# ALIP Phase 2 Implementation Plan

**Version:** 1.0  
**Created:** 2024-01-02  
**Target Completion:** 2024-01-22 (3 weeks)  
**Goal:** Complete all agents and reach v1.0.0 production release

---

## 🎯 Overview

### Current State (v0.2.1 - 60% Complete)
- ✅ Infrastructure complete (state machine, review gates, safety)
- ✅ IngestionAgent working
- ✅ All prompts written
- ✅ All skills implemented
- ✅ Basic CLI working

### Target State (v1.0.0 - 100% Complete)
- ✅ All 5 agents working
- ✅ Full analysis pipeline
- ✅ PDF reports
- ✅ Review CLI commands
- ✅ Comprehensive tests
- ✅ Production-ready documentation

---

## 📅 WEEK 1: Core Analysis Agents

### DAY 1: TopologyAgent - Part 1 (AST Parsing)

**Objective:** Extract code dependencies using AST

**Tasks:**
1. Create `skills/ast_parser.py` (NEW)
   ```python
   def parse_python_imports(file_path: Path) -> List[str]
   def find_function_calls(file_path: Path) -> List[str]
   def extract_sql_queries(file_path: Path) -> List[str]
   ```

2. Write unit tests: `tests/unit/test_ast_parser.py`
   - Test import extraction
   - Test function call detection
   - Test SQL query extraction

3. Create fixture data:
   - `tests/fixtures/sample_code/` with Python files
   - Files with imports, DB calls, function calls

**Deliverables:**
- ✅ `skills/ast_parser.py` (~150 lines)
- ✅ Unit tests (3 tests)
- ✅ Fixture data

**Time:** 6-8 hours

---

### DAY 2: TopologyAgent - Part 2 (Graph Building)

**Objective:** Build dependency graph using networkx

**Tasks:**
1. Implement `agents/topology.py`
   ```python
   class TopologyAgent:
       def build_topology(...) -> AnalysisArtifact:
           # 1. Extract modules from repo
           # 2. Extract tables from DB schema
           # 3. Use AST to find code→DB dependencies
           # 4. Build networkx graph
           # 5. Calculate centrality metrics
           # 6. Detect SPOFs (nodes with high betweenness)
           # 7. Return as DependencyGraph
   ```

2. Write unit tests: `tests/unit/test_topology_agent.py`
   - Test graph construction
   - Test SPOF detection
   - Test circular dependency detection

3. Integration test: `tests/integration/test_topology_workflow.py`
   - End-to-end topology generation
   - Verify artifact structure
   - Check source references

**Deliverables:**
- ✅ `agents/topology.py` (~300 lines)
- ✅ Unit tests (4 tests)
- ✅ Integration test (1 test)

**Dependencies:**
- Day 1 AST parser
- `networkx` library (already in requirements)

**Time:** 6-8 hours

---

### DAY 3: CostAnalysisAgent - Part 1 (Query Analysis)

**Objective:** Analyze query logs for cost drivers

**Tasks:**
1. Enhance `skills/database.py` (EXISTING)
   - Add `rank_queries_by_cost()` function
   - Add `detect_missing_indexes()` function

2. Create `agents/cost_analysis.py`
   ```python
   class CostAnalysisAgent:
       def analyze_costs(...) -> AnalysisArtifact:
           # 1. Load query logs from artifact
           # 2. Calculate: cost = avg_duration_ms × frequency
           # 3. Rank by total cost
           # 4. Classify impact (HIGH/MEDIUM/LOW)
           # 5. Check schema for missing indexes
           # 6. Return top 10 cost drivers
   ```

3. Write unit tests: `tests/unit/test_cost_agent.py`
   - Test cost calculation
   - Test ranking logic
   - Test impact classification

**Deliverables:**
- ✅ Enhanced `skills/database.py` (+100 lines)
- ✅ `agents/cost_analysis.py` (~200 lines)
- ✅ Unit tests (3 tests)

**Time:** 4-6 hours

---

### DAY 4: CostAnalysisAgent - Part 2 (LLM Integration)

**Objective:** Use LLM for pattern analysis and recommendations

**Tasks:**
1. Add LLM integration to CostAnalysisAgent
   ```python
   def _analyze_with_llm(self, cost_drivers: List[CostDriver]) -> List[CostDriver]:
       # Load prompt from prompts/cost_analysis/system_prompt_v1.md
       # Send cost drivers to LLM
       # Parse recommendations
       # Add to cost drivers
   ```

2. Load and version prompts:
   ```python
   def load_prompt(agent_name: str, version: str = "v1") -> str:
       prompt_path = Path(f"prompts/{agent_name}/system_prompt_{version}.md")
       return prompt_path.read_text()
   ```

3. Add to `core/prompt_loader.py` (NEW)

4. Write integration test
   - Mock LLM responses
   - Verify prompt loading
   - Test full cost analysis flow

**Deliverables:**
- ✅ `core/prompt_loader.py` (~50 lines)
- ✅ Enhanced CostAnalysisAgent (+100 lines)
- ✅ Integration test (1 test)

**Dependencies:**
- `core/llm/client.py` (already exists)
- Prompts (already written)

**Time:** 4-6 hours

---

### DAY 5: Integration Testing - Week 1

**Objective:** Verify topology + cost agents work together

**Tasks:**
1. Create `tests/integration/test_analysis_pipeline.py`
   ```python
   def test_topology_feeds_cost_analysis():
       # Run IngestionAgent
       # Run TopologyAgent
       # Run CostAnalysisAgent with topology
       # Verify artifacts link correctly
   ```

2. Test state transitions
   ```python
   def test_state_progression_ingested_to_analyzed():
       # Start at INGESTED
       # Run topology
       # Run cost analysis
       # Verify state is ANALYZED
   ```

3. Test artifact completeness
   ```python
   def test_all_required_artifacts_created():
       # Run pipeline
       # Check topology.json exists
       # Check cost_drivers.json exists
       # Verify all have sources
   ```

4. Fix any bugs found

**Deliverables:**
- ✅ Integration test suite (~200 lines)
- ✅ 3 comprehensive tests
- ✅ Bug fixes from testing

**Time:** 6-8 hours

---

## 📅 WEEK 2: Risk + Synthesis Agents

### DAY 6: RiskAnalysisAgent - Part 1 (Detection Logic)

**Objective:** Implement risk detection patterns

**Tasks:**
1. Create `skills/risk_detector.py` (NEW)
   ```python
   def detect_spofs(topology: DependencyGraph) -> List[Risk]:
       # Find nodes with high betweenness centrality
       # Find single-instance services
       # Return Risk objects
   
   def detect_tribal_knowledge(docs: List[DocArtifact]) -> List[Risk]:
       # Search for "Contact X", "Ask Y"
       # Check last updated dates
       # Return Risk objects
   
   def detect_manual_ops(docs: List[DocArtifact]) -> List[Risk]:
       # Find "manual" processes in runbooks
       # Identify cron jobs requiring parameters
       # Return Risk objects
   
   def detect_security_issues(repo: RepoInventory) -> List[Risk]:
       # Use existing redaction patterns
       # Find hardcoded passwords
       # Find SQL injection patterns
       # Return Risk objects
   ```

2. Write unit tests: `tests/unit/test_risk_detector.py`
   - Test SPOF detection
   - Test tribal knowledge patterns
   - Test security scanning

**Deliverables:**
- ✅ `skills/risk_detector.py` (~250 lines)
- ✅ Unit tests (6 tests)

**Time:** 6-8 hours

---

### DAY 7: RiskAnalysisAgent - Part 2 (Integration)

**Objective:** Complete RiskAnalysisAgent implementation

**Tasks:**
1. Implement `agents/risk_analysis.py`
   ```python
   class RiskAnalysisAgent:
       def analyze_risks(...) -> AnalysisArtifact:
           # 1. Detect SPOFs from topology
           # 2. Scan docs for tribal knowledge
           # 3. Find manual operations
           # 4. Scan code for security issues
           # 5. Classify severity × likelihood
           # 6. Rank risks
           # 7. Return risk register (top 10-15)
   ```

2. Add LLM integration for complex analysis
   ```python
   def _analyze_with_llm(self, risks: List[Risk]) -> List[Risk]:
       # Use prompts/risk_analysis/system_prompt_v1.md
       # Enhance risk descriptions
       # Add mitigation strategies
   ```

3. Write unit tests
4. Write integration test

**Deliverables:**
- ✅ `agents/risk_analysis.py` (~300 lines)
- ✅ Unit tests (4 tests)
- ✅ Integration test (1 test)

**Dependencies:**
- Day 6 risk detector
- TopologyAgent (for SPOFs)

**Time:** 6-8 hours

---

### DAY 8: SynthesisAgent - Part 1 (Data Consolidation)

**Objective:** Consolidate all artifacts

**Tasks:**
1. Implement `agents/synthesis.py`
   ```python
   class SynthesisAgent:
       def generate_executive_summary(...) -> AnalysisArtifact:
           # 1. Load all artifacts from workspace
           # 2. Extract key metrics
           # 3. Identify top 3 findings (mix of cost + risk)
           # 4. Calculate total potential value
           # 5. Prioritize recommendations
   ```

2. Create helper functions
   ```python
   def _select_top_findings(
       cost_drivers: List[CostDriver],
       risks: List[Risk]
   ) -> List[Dict]:
       # Smart selection: 2 high-impact items + 1 critical risk
       # Or: 1 cost + 2 critical risks
       # Based on severity × impact
   
   def _calculate_total_value(cost_drivers: List[CostDriver]) -> float:
       # Sum potential savings
       # Return annual savings estimate
   ```

3. Write unit tests

**Deliverables:**
- ✅ `agents/synthesis.py` (~200 lines)
- ✅ Unit tests (3 tests)

**Time:** 4-6 hours

---

### DAY 9: SynthesisAgent - Part 2 (LLM Report Generation)

**Objective:** Generate executive-quality narratives

**Tasks:**
1. Implement LLM-based report generation
   ```python
   def _generate_with_llm(self, all_artifacts: Dict) -> str:
       # Load prompts/synthesis/system_prompt_v1.md
       # Send consolidated data to LLM
       # Request executive summary (2 pages)
       # Request technical appendix
       # Return markdown content
   ```

2. Create report templates
   ```python
   def _format_executive_summary(self, llm_output: str, metrics: Dict) -> str:
       # Add header with engagement info
       # Add key metrics table
       # Add LLM-generated narrative
       # Add recommended action plan
   
   def _format_technical_appendix(self, all_artifacts: Dict) -> str:
       # Full artifact details
       # Source references
       # Evidence chains
   ```

3. Write integration test
4. Test report quality

**Deliverables:**
- ✅ Enhanced `agents/synthesis.py` (+150 lines)
- ✅ Integration test (1 test)
- ✅ Sample generated report

**Dependencies:**
- All other agents (needs their outputs)
- LLM client

**Time:** 4-6 hours

---

### DAY 10: End-to-End Testing - Week 2

**Objective:** Full pipeline validation

**Tasks:**
1. Create `tests/integration/test_complete_pipeline.py`
   ```python
   def test_full_analysis_pipeline():
       # 1. Create engagement
       # 2. Ingest data
       # 3. Run TopologyAgent
       # 4. Run CostAnalysisAgent
       # 5. Run RiskAnalysisAgent
       # 6. Run SynthesisAgent
       # 7. Verify all artifacts
       # 8. Verify state = ANALYZED
       # 9. Verify report generated
   
   def test_artifact_traceability():
       # Every finding must have sources
       # Every metric must be verifiable
       # No hallucinated data
   
   def test_review_gate_workflow():
       # Submit artifacts for review
       # Approve some, reject some
       # Verify state doesn't progress without approval
   ```

2. Performance testing
   ```python
   def test_analysis_performance():
       # Should complete in < 5 minutes
       # Memory usage < 1GB
       # No memory leaks
   ```

3. Fix any bugs found
4. Optimize slow operations

**Deliverables:**
- ✅ E2E test suite (~300 lines)
- ✅ 4 comprehensive tests
- ✅ Performance benchmarks
- ✅ Bug fixes

**Time:** 6-8 hours

---

## 📅 WEEK 3: CLI, Features & Release

### DAY 11: Review CLI Commands

**Objective:** Add human review workflow to CLI

**Tasks:**
1. Implement review commands in `cli.py`
   ```python
   @main.group()
   def review():
       """Review artifact workflow commands."""
       pass
   
   @review.command()
   @click.option("--engagement", required=True)
   @click.option("--artifact", required=True)
   @click.option("--reviewer", required=True)
   @click.option("--comments", default="")
   def approve(engagement, artifact, reviewer, comments):
       """Approve an artifact."""
       # Load workspace
       # Get ReviewGate
       # Call gate.approve()
       # Show confirmation
   
   @review.command()
   def reject(...):
       """Reject an artifact."""
       pass
   
   @review.command()
   def request_changes(...):
       """Request changes to artifact."""
       pass
   
   @review.command()
   def status(...):
       """Show review status for engagement."""
       # List pending reviews
       # Show approved/rejected counts
       pass
   ```

2. Write CLI tests: `tests/unit/test_cli_review.py`
   - Test approve flow
   - Test reject flow
   - Test status display

3. Update help text and documentation

**Deliverables:**
- ✅ Review CLI commands (~150 lines)
- ✅ CLI tests (3 tests)
- ✅ Updated help text

**Time:** 4-6 hours

---

### DAY 12: PDF Export

**Objective:** Export reports to PDF

**Tasks:**
1. Add weasyprint dependency
   ```toml
   # pyproject.toml
   dependencies = [
       ...,
       "weasyprint>=60.0.0",
   ]
   ```

2. Create `skills/pdf_export.py` (NEW)
   ```python
   def markdown_to_pdf(
       markdown_path: Path,
       output_path: Path,
       css_template: Optional[str] = None
   ) -> Path:
       # Convert markdown to HTML
       # Apply CSS styling
       # Use weasyprint to generate PDF
       # Return output path
   ```

3. Create CSS template: `templates/report.css`
   ```css
   /* Professional report styling */
   @page {
       margin: 2cm;
   }
   h1 { color: #1a5490; }
   table { border-collapse: collapse; }
   /* etc. */
   ```

4. Integrate with SynthesisAgent
   ```python
   def export_to_pdf(self, markdown: str, output_path: Path) -> None:
       # Save markdown to temp file
       # Call pdf_export.markdown_to_pdf()
       # Return path to PDF
   ```

5. Update `report` CLI command
   ```python
   if format == "pdf":
       pdf_path = synthesis_agent.export_to_pdf(...)
       console.print(f"PDF saved: {pdf_path}")
   ```

6. Write tests

**Deliverables:**
- ✅ `skills/pdf_export.py` (~100 lines)
- ✅ CSS template (~50 lines)
- ✅ Integration with CLI
- ✅ Tests (2 tests)

**Time:** 4-6 hours

---

### DAY 13: Documentation Update

**Objective:** Ensure all docs accurate and complete

**Tasks:**
1. Update README.md
   - Complete feature list
   - Updated CLI commands (with examples)
   - Installation with weasyprint
   - New screenshots if possible

2. Update QUICKSTART.md
   - Full workflow example
   - Review workflow example
   - PDF export example

3. Update ARCHITECTURE.md
   - Add agent descriptions
   - Add workflow diagrams (mermaid)
   - Update component list

4. Update IMPLEMENTATION_STATUS.md
   - Mark all agents as complete
   - Update completion percentage to 100%
   - Archive this as historical doc

5. Create CHANGELOG.md entry for v1.0.0
   ```markdown
   ## v1.0.0 - 2024-01-22
   
   ### Added
   - TopologyAgent: Full dependency graph analysis
   - CostAnalysisAgent: Query cost optimization
   - RiskAnalysisAgent: Risk detection and mitigation
   - SynthesisAgent: Executive summary generation
   - Review CLI commands (approve/reject/status)
   - PDF export functionality
   
   ### Fixed
   - All issues from v0.2.1
   
   ### Breaking Changes
   - None (backward compatible with v0.2.1)
   ```

6. Create MIGRATION.md (v0.2.1 → v1.0.0)

**Deliverables:**
- ✅ Updated README.md
- ✅ Updated QUICKSTART.md
- ✅ Updated ARCHITECTURE.md
- ✅ Updated CHANGELOG.md
- ✅ New MIGRATION.md

**Time:** 4-6 hours

---

### DAY 14: Final Testing & Bug Fixes

**Objective:** Complete test coverage and fix all bugs

**Tasks:**
1. Run complete test suite
   ```bash
   pytest -v --cov=core --cov=skills --cov=agents --cov-report=html
   ```

2. Achieve >85% coverage
   - Add missing unit tests
   - Add missing integration tests

3. Test on fresh environment
   ```bash
   # Clean install test
   python -m venv fresh_env
   source fresh_env/bin/activate
   pip install -e .
   alip --help
   # Run demo
   ```

4. Fix any discovered bugs

5. Performance optimization
   - Profile slow operations
   - Optimize if needed

6. Create comprehensive demo
   ```bash
   # Demo script: demo.sh
   #!/bin/bash
   alip new --name "Acme Corp" --id acme-001
   alip ingest --engagement acme-001 \
     --repo demo_data/sample_repo \
     --db-schema demo_data/schema.sql \
     --query-logs demo_data/queries.json \
     --docs demo_data/docs
   alip analyze --engagement acme-001
   alip review status --engagement acme-001
   alip review approve --engagement acme-001 --artifact topology --reviewer "John Doe"
   alip report --engagement acme-001 --format pdf
   ```

**Deliverables:**
- ✅ >85% test coverage
- ✅ All bugs fixed
- ✅ Demo script working
- ✅ Performance benchmarks

**Time:** 6-8 hours

---

### DAY 15: Release Preparation

**Objective:** Package and release v1.0.0

**Tasks:**
1. Update version everywhere
   - `pyproject.toml`: version = "1.0.0"
   - `__init__.py`: __version__ = "1.0.0"

2. Create release notes: `RELEASE_NOTES_v1.0.0.md`
   ```markdown
   # ALIP v1.0.0 - Production Release
   
   ## What's New
   - Complete analysis pipeline
   - 5 production-ready agents
   - PDF export
   - Review workflow
   
   ## Migration from v0.2.1
   See MIGRATION.md
   
   ## Installation
   ...
   ```

3. Package release
   ```bash
   # Create archives
   tar -czf alip-v1.0.0.tar.gz alip/
   zip -r alip-v1.0.0.zip alip/
   
   # Create checksums
   sha256sum alip-v1.0.0.tar.gz > checksums.txt
   sha256sum alip-v1.0.0.zip >> checksums.txt
   ```

4. Create demo video/walkthrough
   - Record terminal session
   - Show complete workflow
   - Demonstrate PDF output
   - Show review workflow

5. Create deployment guide
   - Production setup
   - Environment variables
   - Database connection setup
   - Scaling considerations

**Deliverables:**
- ✅ Release packages (.tar.gz, .zip)
- ✅ Release notes
- ✅ Checksums
- ✅ Demo video/guide
- ✅ Deployment guide

**Time:** 4-6 hours

---

## 📊 Testing Strategy

### Unit Tests (Target: 50+ tests)

**By Module:**
- `core/`: 15 tests (state machine, review gate, skill output)
- `skills/`: 20 tests (workspace, repo, database, documents, ast_parser, risk_detector, pdf_export)
- `agents/`: 15 tests (all 5 agents - 3 tests each)
- `cli/`: 5 tests (review commands)

**Total:** ~55 unit tests

### Integration Tests (Target: 15+ tests)

**Coverage:**
- Ingestion workflow (existing)
- Topology workflow (new)
- Cost analysis workflow (new)
- Risk analysis workflow (new)
- Synthesis workflow (new)
- Complete pipeline (new)
- Review gate workflow (new)
- E2E with PDF export (new)
- State machine compliance (new)
- Artifact traceability (new)

**Total:** ~15 integration tests

### Test Pyramid

```
        E2E Tests (5)
       /           \
    Integration (15)
   /                 \
  Unit Tests (55)
```

---

## 📦 Dependencies to Add

```toml
[project]
dependencies = [
    # Existing
    "pydantic>=2.0.0",
    "click>=8.1.0",
    "rich>=13.0.0",
    "pyyaml>=6.0",
    "gitpython>=3.1.0",  # Now optional
    "sqlparse>=0.4.0",
    "PyPDF2>=3.0.0",
    "python-docx>=1.0.0",
    "jinja2>=3.1.0",
    "anthropic>=0.18.0",
    
    # NEW for Phase 2
    "networkx>=3.0",  # Topology graphs
    "weasyprint>=60.0.0",  # PDF export
    "markdown>=3.5.0",  # Markdown to HTML for PDF
]
```

---

## 🎯 Success Criteria

### v1.0.0 Definition of Done

**Must Have:**
- ✅ All 5 agents implemented and tested
- ✅ CLI commands complete (new, ingest, analyze, report, review, run)
- ✅ PDF export working
- ✅ >85% test coverage
- ✅ All E2E tests passing
- ✅ State machine enforcing full lifecycle
- ✅ Documentation complete and accurate

**Quality Gates:**
- ✅ Demo script runs end-to-end without errors
- ✅ Analysis completes in <5 minutes
- ✅ Memory usage <1GB for typical engagement
- ✅ All artifacts have source references
- ✅ All reports are client-ready quality

**Test:**
```bash
# This must work perfectly:
./demo.sh

# Output should include:
# - All artifacts in workspace/
# - PDF report generated
# - Review workflow demonstrated
# - No errors or warnings
```

---

## 🚧 Risk Mitigation

### Identified Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM API rate limits | High | Medium | Add retry logic, local fallback |
| Weasyprint install issues | Medium | Medium | Document platform-specific steps |
| Test coverage gaps | Medium | Low | Daily coverage checks |
| Performance issues | High | Low | Benchmark early, optimize iteratively |
| Scope creep | High | Medium | Strict adherence to plan |

### Contingency Plans

**If Behind Schedule:**
1. Defer PDF export to v1.1 (markdown is enough for MVP)
2. Simplify LLM integration (use templates first)
3. Reduce test coverage target to 75%

**If LLM Issues:**
1. Use template-based generation as fallback
2. Add mock LLM client for testing
3. Make LLM optional with degraded functionality

**If Dependency Issues:**
1. Make weasyprint optional (like GitPython)
2. Provide manual PDF conversion steps
3. Focus on core analysis pipeline

---

## 📈 Progress Tracking

### Daily Checklist Template

```markdown
## Day X: [Component Name]

**Date:** YYYY-MM-DD
**Status:** 🟢 On Track / 🟡 At Risk / 🔴 Blocked

### Completed
- [ ] Implementation (X lines)
- [ ] Unit tests (X tests)
- [ ] Integration tests (X tests)
- [ ] Documentation update

### Blockers
- None / [Description]

### Tomorrow
- [Next task]

### Notes
- [Observations, learnings, etc.]
```

### Weekly Review

**End of Week 1:**
- TopologyAgent complete?
- CostAnalysisAgent complete?
- Integration tests passing?

**End of Week 2:**
- RiskAnalysisAgent complete?
- SynthesisAgent complete?
- E2E tests passing?

**End of Week 3:**
- Review CLI working?
- PDF export working?
- All docs updated?
- Release ready?

---

## 🎓 Learning Resources

### For Implementers

**AST Parsing:**
- Python `ast` module docs
- Tree walking patterns

**NetworkX:**
- Graph creation tutorial
- Centrality metrics guide

**LLM Integration:**
- Anthropic API docs
- Prompt engineering best practices

**PDF Generation:**
- Weasyprint documentation
- CSS for print media

---

## 📞 Support & Questions

**During Implementation:**
1. Check this plan first
2. Review ARCHITECTURE.md
3. Study IngestionAgent as reference
4. Read relevant prompts
5. Check existing skill implementations

**If Stuck:**
1. Write the test first (TDD)
2. Start with simplest version
3. Add complexity incrementally
4. Commit working code frequently

---

## 🎉 Expected Outcomes

### By End of Week 1:
- Topology + Cost agents working
- Can generate dependency graphs
- Can identify cost drivers
- 50% of Phase 2 complete

### By End of Week 2:
- Risk + Synthesis agents working
- Full analysis pipeline functional
- Executive summaries generated
- 85% of Phase 2 complete

### By End of Week 3:
- Review workflow complete
- PDF export working
- All docs updated
- v1.0.0 released
- 100% of Phase 2 complete

---

## 📄 Appendix: Code Templates

### Agent Template
```python
"""[Agent Name] - [One-line description]."""

from pathlib import Path
from typing import Any, List

from core.models import AnalysisArtifact
from core.skill_output import SkillOutput
from core.prompt_loader import load_prompt


class [Agent]Agent:
    """[Description]."""

    def __init__(self, workspace_paths: Any, engagement_config: Any):
        self.workspace = workspace_paths
        self.config = engagement_config
        self.prompt = load_prompt("[agent_name]", "v1")

    def [main_method](...) -> AnalysisArtifact:
        """[Description].
        
        Args:
            ...
            
        Returns:
            AnalysisArtifact with ...
        """
        # 1. Load inputs
        # 2. Process with skills
        # 3. Use LLM if needed
        # 4. Create artifact
        # 5. Return
        
        raise NotImplementedError()
```

### Test Template
```python
"""Tests for [Component]."""

import pytest
from pathlib import Path


@pytest.fixture
def sample_data():
    """Create sample test data."""
    return {...}


def test_[functionality](sample_data):
    """Test [what]."""
    # Arrange
    ...
    
    # Act
    result = ...
    
    # Assert
    assert ...


def test_[error_case]():
    """Test [error handling]."""
    with pytest.raises(SomeError):
        ...
```

---

**Total Plan Pages:** 15  
**Total Tasks:** ~60  
**Total Estimated Hours:** 100-120 hours (15 days × 7-8 hours)  
**Confidence Level:** HIGH (all infrastructure ready, clear path forward)

---

*This plan is a living document. Update as needed during implementation.*
