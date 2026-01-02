# ALIP - AI-Assisted Legacy Intelligence Platform

**Version:** 0.1.0 (MVP)  
**Status:** Build-Ready  
**License:** Proprietary

> Trust-first, read-only AI-assisted intelligence for legacy systems

---

## Overview

ALIP provides **AI-assisted, read-only intelligence** over legacy systems (ERP, CRM, custom databases, batch jobs) that:

- ✅ Surfaces cost, risk, and optimization opportunities
- ✅ Preserves system safety (read-only by default)
- ✅ Keeps humans in control (review gates)
- ✅ Produces executive-grade outputs
- ✅ Maintains full traceability

**Target Market:** Mid-sized enterprises (50-500 employees) with poorly documented legacy systems.

---

## Key Features

### MVP (Current)
- ✅ Workspace management and engagement tracking
- ✅ Multi-source data ingestion (repos, databases, documents)
- ✅ Automatic redaction of sensitive information
- ✅ Repository analysis and language detection
- ✅ Database schema parsing (JSON/SQL DDL)
- ✅ Query log analysis and cost estimation
- ✅ Document ingestion (PDF, DOCX, Markdown, TXT)
- ✅ Structured artifact generation with source tracking
- ✅ CLI interface for all operations

### Coming Soon
- ⏳ Topology graph construction
- ⏳ Cost driver analysis
- ⏳ Risk assessment (SPOFs, tribal knowledge)
- ⏳ AI opportunity identification
- ⏳ Executive summary generation
- ⏳ PDF report generation

---

## Architecture

### Core Principles
1. **Read-Only First** - No writes to client systems
2. **Human-in-the-Loop** - All insights require review
3. **Traceable** - Every output references sources
4. **Safe** - Redaction and isolation by default

### Components

```
alip/
├── core/              # Core models, utilities, LLM client
├── agents/            # Analysis agents (ingestion, topology, etc.)
├── skills/            # Reusable functions (repo, db, docs)
├── connectors/        # External system connectors (future)
├── pipelines/         # Orchestration workflows (future)
├── reports/           # Report generation (future)
├── prompts/           # LLM prompts (versioned)
└── tests/             # Unit and integration tests
```

---

## Quick Start

### Installation

```bash
# Clone repository
git clone <repo-url>
cd alip

# Install dependencies
pip install -e ".[dev]"

# Set up API key (if using Claude)
export ANTHROPIC_API_KEY="your-key-here"
```

### Basic Usage

```bash
# 1. Create new engagement
alip new --name "Acme Corp" --id acme-2024-001

# 2. Ingest data sources
alip ingest --engagement acme-2024-001 \
  --repo /path/to/legacy/code \
  --db-schema /path/to/schema.sql \
  --query-logs /path/to/queries.json \
  --docs /path/to/documentation

# 3. Analyze (coming soon)
alip analyze --engagement acme-2024-001

# 4. Generate reports (coming soon)
alip report --engagement acme-2024-001 --format md

# List all engagements
alip list
```

---

## Data Ingestion

### Supported Data Sources

| Source Type | Formats | Description |
|------------|---------|-------------|
| **Repository** | Git repos | Code, dependencies, structure |
| **Database Schema** | JSON, SQL DDL | Tables, columns, indexes, relationships |
| **Query Logs** | JSON, TXT | Execution history, performance data |
| **Documents** | PDF, DOCX, MD, TXT | Runbooks, architecture docs |

### Example Ingestion

```bash
# Repository only
alip ingest --engagement demo-001 --repo ./legacy-erp

# Multiple sources
alip ingest --engagement demo-001 \
  --repo ./code \
  --db-schema ./exports/schema.json \
  --query-logs ./logs/queries.json \
  --docs ./documentation
```

---

## Configuration

### Engagement Configuration

Each engagement has a configuration file at `workspace/<engagement-id>/config/engagement.json`:

```json
{
  "engagement_id": "demo-001",
  "client_name": "Demo Corp",
  "read_only_mode": true,
  "redaction_enabled": true,
  "store_raw_data": false,
  "output_formats": ["md", "json"],
  "locale": "en"
}
```

### Locale Support

- `en` - English (default)
- `de` - German (DACH market: emphasis on compliance)
- Other locales can be added in `PRD_Addendum_<Country>.md`

---

## Safety & Compliance

### Read-Only Guarantee

```python
# All agents enforce read-only mode
assert config.read_only_mode == True

# No write operations are ever performed
# Database connections are read-only
# Repository access is clone-based only
```

### Data Redaction

Automatic redaction of:
- ✅ Email addresses
- ✅ API keys and tokens
- ✅ Passwords
- ✅ AWS credentials
- ✅ Custom patterns (configurable)

### Audit Trail

Every artifact includes:
- Source references (file, line, timestamp)
- Processing timestamp
- Review status
- Confidence level

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=alip --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_workspace.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking (future)
mypy alip/
```

### Project Structure

```
tests/
├── unit/              # Unit tests for skills and utilities
│   ├── test_workspace.py
│   ├── test_repo.py
│   ├── test_database.py
│   └── test_utils.py
├── integration/       # Integration tests (future)
└── fixtures/          # Sample data for testing
```

---

## Example Workflow

### 1. Create Engagement

```bash
$ alip new --name "Legacy ERP Analysis" --id erp-2024-001

Creating new engagement: Legacy ERP Analysis (erp-2024-001)

✓ Workspace created: ./workspace/erp-2024-001

Directory Structure:
  • Config:     workspace/erp-2024-001/config
  • Raw:        workspace/erp-2024-001/raw
  • Processed:  workspace/erp-2024-001/processed
  • Artifacts:  workspace/erp-2024-001/artifacts
  • Reports:    workspace/erp-2024-001/reports
```

### 2. Ingest Data

```bash
$ alip ingest --engagement erp-2024-001 \
  --repo /opt/legacy/erp-core \
  --db-schema exports/schema.sql

Ingesting data for: Legacy ERP Analysis
Engagement ID: erp-2024-001

→ Ingesting repository...
  ✓ Repository: 1,247 files

→ Ingesting database schema...
  ✓ Schema: 42 tables

✓ Ingestion complete
Artifacts saved to: workspace/erp-2024-001/artifacts
```

### 3. Review Artifacts

```bash
$ ls workspace/erp-2024-001/artifacts/

repo_inventory.json         # Structured data
repo_inventory.md          # Human-readable
repo_inventory_sources.json # Source references
repo_inventory_metrics.json # Metrics

db_schema.json
db_schema.md
db_schema_sources.json
db_schema_metrics.json
```

---

## Artifacts

### Artifact Types

Each analysis produces standardized artifacts:

1. **JSON** - Structured data for programmatic use
2. **Markdown** - Human-readable summary
3. **Sources** - Full source traceability
4. **Metrics** - Key performance indicators

### Example Artifact

```json
{
  "artifact_type": "repo_inventory",
  "engagement_id": "demo-001",
  "created_at": "2024-01-01T10:00:00",
  "data": {
    "total_files": 1247,
    "languages": {"Python": 450, "JavaScript": 320},
    "lines_of_code": 125000
  },
  "sources": [
    {
      "type": "repo",
      "path": "/opt/legacy/erp-core",
      "timestamp": "2024-01-01T10:00:00"
    }
  ],
  "metrics": {
    "total_files": 1247,
    "total_lines": 125000,
    "language_count": 5
  },
  "review_status": "pending"
}
```

---

## Roadmap

### Phase 1 (Current - MVP)
- [x] Workspace management
- [x] Data ingestion (repo, DB, docs)
- [x] Redaction and safety
- [x] CLI interface
- [ ] Topology analysis
- [ ] Cost/risk analysis
- [ ] Report generation

### Phase 2 (Next)
- [ ] Continuous monitoring (read-only)
- [ ] LLM-powered insights
- [ ] Executive dashboards
- [ ] Multi-engagement comparison

### Phase 3 (Future)
- [ ] Safe optimization recommendations
- [ ] Change impact simulation
- [ ] Integration with CI/CD
- [ ] API access

---

## Market Positioning

### Germany (DACH)
- **Focus:** Compliance, traceability, documentation
- **Positioning:** "AI-assisted legacy cost & risk audit"
- **Emphasis:** GDPR compliance, EU AI Act alignment

### USA
- **Focus:** ROI, speed, quantified savings
- **Positioning:** "Reduce legacy costs by 20-40% in 90 days"
- **Emphasis:** Fast pilots, measurable outcomes

### India
- **Focus:** Cost reduction, automation
- **Positioning:** "Reduce legacy IT workload without migration"
- **Emphasis:** Documentation generation, operational efficiency

---

## Support

### Documentation
- [Product Requirements](PRD_AI_Assisted_Legacy_Intelligence_Core.txt)
- [Contributing Guidelines](CONTRIBUTING.md)
- [Architecture Decision Records](docs/adr/) (future)

### Contact
For questions or support, contact the ALIP team.

---

## License

Proprietary - All Rights Reserved

---

**Built with safety, transparency, and trust at the core.**
