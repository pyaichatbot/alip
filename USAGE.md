# ALIP Usage Guide

Complete guide to using ALIP for legacy system analysis.

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Complete Workflow](#complete-workflow)
4. [Command Reference](#command-reference)
5. [Data Preparation](#data-preparation)
6. [Understanding Outputs](#understanding-outputs)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager
- Git (optional, for repository analysis)

### Install ALIP

```bash
# Clone the repository
git clone <repo-url>
cd alip

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Verify installation
alip --version
```

### Set Up API Key (Optional)

If using LLM features (recommendations, executive summaries):

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

---

## Quick Start

### 5-Minute Demo

```bash
# 1. Generate sample data
python create_demo_data.py

# 2. Create engagement
alip new --name "Demo Corp" --id demo-001

# 3. Ingest data
alip ingest --engagement demo-001 \
  --repo demo_data/sample_repo \
  --db-schema demo_data/schema.sql \
  --query-logs demo_data/queries.json \
  --docs demo_data/docs

# 4. Analyze
alip analyze --engagement demo-001

# 5. Generate reports
alip report --engagement demo-001

# 6. View results
ls workspace/demo-001/artifacts/
ls workspace/demo-001/reports/
```

---

## Complete Workflow

### Step 1: Create Engagement

```bash
alip new --name "Enterprise Corp" --id ent-001 --locale en
```

**Output:**
```
Creating new engagement: Enterprise Corp (ent-001)

✓ Workspace created: ./workspace/ent-001

Directory Structure:
  • Config:     workspace/ent-001/config
  • Raw:        workspace/ent-001/raw
  • Processed:  workspace/ent-001/processed
  • Artifacts:  workspace/ent-001/artifacts
  • Reports:    workspace/ent-001/reports
```

### Step 2: Ingest Data Sources

```bash
alip ingest --engagement ent-001 \
  --repo /path/to/legacy/code \
  --db-schema /path/to/schema.sql \
  --query-logs /path/to/queries.json \
  --docs /path/to/documentation
```

**What Gets Ingested:**

| Source | Formats | Description |
|--------|---------|-------------|
| **Repository** | Git repos, code directories | Code structure, dependencies, languages |
| **Database Schema** | SQL DDL, JSON | Tables, columns, indexes, relationships |
| **Query Logs** | JSON, TXT | Query execution history, performance data |
| **Documents** | PDF, DOCX, MD, TXT | Runbooks, architecture docs, READMEs |

**Output:**
```
Ingesting data for: Enterprise Corp
Engagement ID: ent-001

→ Ingesting repository...
  ✓ Repository: 1,247 files

→ Ingesting database schema...
  ✓ Schema: 42 tables

→ Ingesting query logs...
  ✓ Queries: 5,000 logged

→ Ingesting documents...
  ✓ Documents: 12 files

✓ Ingestion complete
Artifacts saved to: workspace/ent-001/artifacts
```

### Step 3: Analyze System

```bash
alip analyze --engagement ent-001
```

**What Gets Analyzed:**

1. **Topology Analysis** - System dependency graph
   - Component relationships
   - Single points of failure (SPOFs)
   - Circular dependencies

2. **Cost Analysis** - Performance bottlenecks
   - Slow/frequent queries
   - Missing indexes
   - Total execution cost

3. **Risk Analysis** - Operational and technical risks
   - Security vulnerabilities
   - Tribal knowledge dependencies
   - Manual operations
   - Documentation gaps

**Output:**
```
Analyzing engagement: Enterprise Corp

→ Loading artifacts...
  ✓ Repository: 1,247 files
  ✓ Database: 42 tables

→ Building system topology...
  ✓ Topology complete:
    • 156 components
    • 342 dependencies
    • 3 SPOFs detected

→ Cost analysis...
  ✓ Cost analysis complete:
    • 8 cost drivers identified
    • 3 high impact drivers
    • Total cost: 45.2s

→ Risk assessment...
  ✓ Risk assessment complete:
    • 12 risks identified
    • 2 critical risks
    • 5 high severity risks

✓ Analysis complete!
State updated: analyzed
```

### Step 4: Generate Reports

```bash
alip report --engagement ent-001
```

**Output:**
```
Generating report for: Enterprise Corp

→ Loading analysis artifacts...
  ✓ Loaded topology metrics
  ✓ Loaded 8 cost drivers
  ✓ Loaded 12 risks

→ Generating executive summary and reports...
  ✓ Executive summary generated
  ✓ Technical appendix generated
  ✓ Action plan generated

✓ Report generation complete!

Generated Reports:
  • Executive Summary: workspace/ent-001/reports/executive_summary.md
  • Technical Appendix: workspace/ent-001/reports/technical_appendix.md
  • Action Plan: workspace/ent-001/reports/action_plan.md
```

---

## Command Reference

### `alip new`

Create a new engagement workspace.

```bash
alip new --name "Client Name" --id engagement-id [--locale en] [--workspace ./workspace]
```

**Options:**
- `--name` (required): Client/company name
- `--id` (required): Unique engagement ID
- `--locale` (optional): Language locale (en, de, etc.)
- `--workspace` (optional): Workspace base directory (default: ./workspace)

### `alip ingest`

Ingest data sources for analysis.

```bash
alip ingest --engagement ID [--repo PATH] [--db-schema PATH] [--query-logs PATH] [--docs PATH] [--workspace PATH]
```

**Options:**
- `--engagement` (required): Engagement ID
- `--repo`: Path to repository or code directory
- `--db-schema`: Path to database schema file (SQL or JSON)
- `--query-logs`: Path to query log file (JSON or TXT)
- `--docs`: Path to documentation directory
- `--workspace`: Workspace base directory

**Note:** At least one data source must be provided.

### `alip analyze`

Run analysis on ingested data.

```bash
alip analyze --engagement ID [--workspace PATH]
```

**What it does:**
1. Loads ingested artifacts
2. Builds system topology
3. Analyzes costs and performance
4. Assesses risks
5. Generates analysis artifacts

### `alip report`

Generate executive and technical reports.

```bash
alip report --engagement ID [--format md] [--workspace PATH]
```

**Options:**
- `--engagement` (required): Engagement ID
- `--format`: Report format (md or pdf) - PDF coming soon
- `--workspace`: Workspace base directory

**Generates:**
- Executive Summary (2-3 pages)
- Technical Appendix (detailed findings)
- Action Plan (prioritized roadmap)

### `alip list`

List all engagements.

```bash
alip list [--workspace PATH]
```

---

## Data Preparation

### Repository

**What to provide:**
- Path to Git repository root, OR
- Path to code directory (Git not required)

**What ALIP does:**
- Scans recursively for code files
- Detects programming languages
- Extracts imports and dependencies
- Skips common exclusions (.git, node_modules, etc.)

**Tips:**
- Include all relevant code directories
- Exclude build artifacts and dependencies
- Ensure code is readable (not obfuscated)

### Database Schema

**SQL DDL Format:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255),
    name VARCHAR(255)
);

CREATE INDEX idx_users_email ON users(email);
```

**Export commands:**
```bash
# PostgreSQL
pg_dump --schema-only dbname > schema.sql

# MySQL
mysqldump --no-data dbname > schema.sql

# SQLite
sqlite3 dbname .schema > schema.sql
```

**JSON Format:**
```json
{
  "database_name": "mydb",
  "tables": [
    {
      "name": "users",
      "columns": [
        {"name": "id", "type": "INTEGER", "primary_key": true},
        {"name": "email", "type": "VARCHAR(255)"}
      ],
      "indexes": [
        {"name": "idx_users_email", "columns": ["email"]}
      ]
    }
  ]
}
```

### Query Logs

**JSON Format:**
```json
[
  {
    "query": "SELECT * FROM users WHERE email = ?",
    "timestamp": "2024-01-02T10:00:00",
    "duration_ms": 150.0
  }
]
```

**Text Format:**
```
2024-01-02 10:00:00 | SELECT * FROM users WHERE email = 'test@example.com' | 150ms
```

**What to include:**
- Recent query history (last 7-30 days)
- All query types (SELECT, INSERT, UPDATE, DELETE)
- Execution times and frequencies

### Documentation

**Supported formats:**
- PDF (.pdf)
- Word documents (.docx)
- Markdown (.md)
- Plain text (.txt)

**What to gather:**
- Architecture documentation
- Runbooks and operational guides
- README files
- API documentation
- Deployment procedures

**Tips:**
- Place all documents in a single directory
- Use descriptive filenames
- Include both high-level and detailed docs

---

## Understanding Outputs

### Complete Output Package

After running the complete workflow, you receive **22 artifacts**:

#### For Executives

1. **executive_summary.md** - 2-3 page overview
   - Executive overview
   - Key findings
   - Business impact
   - Recommended actions
   - Next steps

2. **action_plan.md** - Phased roadmap
   - Phase 1: Quick wins (1-2 weeks)
   - Phase 2: Core improvements (1-3 months)
   - Phase 3: Strategic initiatives (3-6 months)
   - Success metrics

#### For Technical Teams

3. **technical_appendix.md** - Detailed findings
   - System architecture analysis
   - Performance & cost analysis
   - Risk assessment
   - Detailed recommendations

4. **topology.md** - System architecture map
   - Component graph
   - Dependency relationships
   - SPOF identification

5. **cost_drivers.md** - Performance analysis
   - Top cost drivers
   - Query patterns
   - Optimization opportunities

6. **risk_register.md** - Risk assessment
   - All identified risks
   - Severity and confidence
   - Mitigation strategies

#### For Compliance

7. **All *_sources.json** - Full traceability
   - Source references for every finding
   - File paths, line numbers, timestamps

8. **All *_metrics.json** - Quantified results
   - Key performance indicators
   - Summary statistics

9. **All main artifact JSON files** - Structured data
   - Machine-readable format
   - For programmatic use

### Artifact Structure

Each analysis produces 4 files:

```
artifacts/
├── artifact_name.json        # Structured data
├── artifact_name.md          # Human-readable summary
├── artifact_name_sources.json # Source traceability
└── artifact_name_metrics.json # Key metrics
```

### Example: Repository Inventory

**repo_inventory.json** (Machine-readable):
```json
{
  "artifact_type": "repo_inventory",
  "engagement_id": "ent-001",
  "data": {
    "total_files": 1247,
    "languages": {"Python": 450, "JavaScript": 320},
    "lines_of_code": 125000
  },
  "sources": [
    {
      "type": "repo",
      "path": "/path/to/repo",
      "timestamp": "2024-01-01T10:00:00"
    }
  ],
  "metrics": {
    "total_files": 1247,
    "total_lines": 125000
  }
}
```

**repo_inventory.md** (Human-readable):
```markdown
# Repository Inventory

**Engagement ID:** ent-001
**Created:** 2024-01-01T10:00:00

## Metrics
- **Total Files:** 1,247
- **Lines of Code:** 125,000
- **Languages:** Python (450), JavaScript (320)
```

---

## Configuration

### Engagement Configuration

Each engagement has a configuration file at:
```
workspace/<engagement-id>/config/engagement.json
```

**Default configuration:**
```json
{
  "engagement_id": "ent-001",
  "client_name": "Enterprise Corp",
  "read_only_mode": true,
  "redaction_enabled": true,
  "store_raw_data": false,
  "output_formats": ["md", "json"],
  "locale": "en",
  "state": "new"
}
```

**Configuration options:**
- `read_only_mode`: Always `true` (safety requirement)
- `redaction_enabled`: Automatically redact sensitive data
- `store_raw_data`: Whether to keep original inputs
- `output_formats`: Output formats (md, json, pdf)
- `locale`: Language preference (en, de, etc.)

### Locale Support

- **en** (English) - Default, business-focused
- **de** (German) - DACH market, compliance-focused

---

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Ensure package is installed
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Permission errors:**
```bash
# Check workspace permissions
ls -la workspace/

# Fix permissions if needed
chmod -R 755 workspace/
```

**Missing dependencies:**
```bash
# Reinstall all dependencies
pip install -r requirements.txt
pip install -e ".[dev]"
```

**LLM errors:**
```bash
# Check API key is set
echo $ANTHROPIC_API_KEY

# If not set, ALIP will use template-based generation (no LLM)
```

**State transition errors:**
```bash
# Check current state
cat workspace/<engagement-id>/config/engagement.json | grep state

# Must follow: new → ingested → analyzed → reviewed → finalized
```

### Getting Help

- Check [README.md](README.md) for project overview
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development guide

---

## Best Practices

### Data Quality

1. **Provide complete data** - More data = better analysis
2. **Use recent query logs** - Last 7-30 days is ideal
3. **Include all documentation** - Even outdated docs are valuable
4. **Export full schemas** - Include all tables and indexes

### Engagement Management

1. **Use descriptive IDs** - `client-year-001` format
2. **One engagement per system** - Don't mix systems
3. **Keep workspace clean** - Archive old engagements
4. **Review artifacts** - Check quality before proceeding

### Analysis Workflow

1. **Ingest all sources** - Repository, schema, logs, docs
2. **Review ingestion artifacts** - Verify data quality
3. **Run analysis** - Let all agents complete
4. **Review analysis results** - Check findings
5. **Generate reports** - Create executive deliverables

---

## Next Steps

After completing your first analysis:

1. **Review executive summary** - Understand key findings
2. **Share with stakeholders** - Executive and technical teams
3. **Prioritize action plan** - Focus on quick wins first
4. **Track progress** - Use success metrics
5. **Re-analyze periodically** - Monitor improvements

---

**Ready to analyze your legacy systems! 🚀**

