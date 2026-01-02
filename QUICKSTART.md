# ALIP Quick Start Guide

Get up and running with ALIP in 5 minutes.

---

## Prerequisites

- Python 3.10 or higher
- pip package manager
- Git (optional, for repository analysis)

---

## Installation

### Option 1: Development Install (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd alip

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Verify installation
alip --version
```

### Option 2: Production Install

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Install the package
pip install -e .
```

---

## First Engagement (Demo)

### Step 1: Create Demo Data

```bash
# Generate sample legacy system data
python create_demo_data.py
```

This creates:
- Sample Python codebase with legacy patterns
- Database schema (SQL DDL)
- Query execution logs
- Documentation files

### Step 2: Create Engagement

```bash
alip new --name "Demo Corp" --id demo-001
```

Expected output:
```
Creating new engagement: Demo Corp (demo-001)

✓ Workspace created: ./workspace/demo-001

Directory Structure:
  • Config:     workspace/demo-001/config
  • Raw:        workspace/demo-001/raw
  • Processed:  workspace/demo-001/processed
  • Artifacts:  workspace/demo-001/artifacts
  • Reports:    workspace/demo-001/reports
```

### Step 3: Ingest Data

```bash
alip ingest --engagement demo-001 \
  --repo demo_data/sample_repo \
  --db-schema demo_data/schema.sql \
  --query-logs demo_data/queries.json \
  --docs demo_data/docs
```

Expected output:
```
Ingesting data for: Demo Corp
Engagement ID: demo-001

→ Ingesting repository...
  ✓ Repository: 4 files

→ Ingesting database schema...
  ✓ Schema: 4 tables

→ Ingesting query logs...
  ✓ Queries: 5 logged

→ Ingesting documents...
  ✓ Documents: 2 files

✓ Ingestion complete
Artifacts saved to: workspace/demo-001/artifacts
```

### Step 4: Explore Results

```bash
# List all engagements
alip list

# View generated artifacts
ls workspace/demo-001/artifacts/

# View human-readable summaries
cat workspace/demo-001/artifacts/repo_inventory.md
cat workspace/demo-001/artifacts/db_schema.md
```

---

## Real-World Usage

### Analyzing Your Legacy System

```bash
# 1. Create engagement for your project
alip new --name "Your Company Legacy ERP" --id erp-2024-001

# 2. Ingest your actual data
alip ingest --engagement erp-2024-001 \
  --repo /path/to/your/legacy/code \
  --db-schema /path/to/schema/export.sql \
  --query-logs /path/to/query/logs.json \
  --docs /path/to/documentation

# 3. Review artifacts
ls workspace/erp-2024-001/artifacts/
```

### Data Preparation Tips

**Repository:**
- Provide path to Git repository root
- Or provide path to code directory (Git not required)
- ALIP will scan recursively, skipping common exclusions

**Database Schema:**
- Export as SQL DDL: `pg_dump --schema-only dbname > schema.sql`
- Or export as JSON with table/column metadata
- Format: `{database_name, tables, indexes, relationships}`

**Query Logs:**
- Export recent query history (last 7-30 days)
- JSON format: `[{query, timestamp, duration_ms}]`
- Or text logs (one query per line)

**Documentation:**
- Gather: runbooks, architecture docs, READMEs
- Formats: PDF, DOCX, Markdown, plain text
- Place all in single directory

---

## Configuration

### Engagement Settings

Edit `workspace/<engagement-id>/config/engagement.json`:

```json
{
  "engagement_id": "demo-001",
  "client_name": "Demo Corp",
  "read_only_mode": true,           // Always true for safety
  "redaction_enabled": true,        // Redact sensitive data
  "store_raw_data": false,          // Don't store raw inputs
  "output_formats": ["md", "json"], // Output formats
  "locale": "en"                    // Language preference
}
```

### Locale Options

- `en` - English (default)
- `de` - German (DACH compliance focus)

More locales can be added via PRD addendums.

---

## Understanding Artifacts

Each ingestion creates 4 files per source:

```
artifacts/
├── repo_inventory.json        # Structured data
├── repo_inventory.md          # Human-readable summary
├── repo_inventory_sources.json # Source traceability
└── repo_inventory_metrics.json # Key metrics
```

### Example: Repository Inventory

**repo_inventory.json** - Machine-readable:
```json
{
  "artifact_type": "repo_inventory",
  "engagement_id": "demo-001",
  "data": {
    "total_files": 1247,
    "languages": {"Python": 450, "JavaScript": 320},
    "lines_of_code": 125000
  },
  "metrics": {
    "total_files": 1247,
    "total_lines": 125000
  }
}
```

**repo_inventory.md** - Human-readable:
```markdown
# Repo Inventory

**Engagement ID:** demo-001
**Created:** 2024-01-01T10:00:00

## Metrics
- **total_files:** 1247
- **total_lines:** 125000
- **language_count:** 5

## Sources
- repo: `/path/to/repo`
```

---

## Next Steps

### Current MVP Features

✅ **Available Now:**
- Workspace management
- Multi-source data ingestion
- Automatic redaction
- Repository analysis
- Database schema parsing
- Query log analysis
- Document ingestion

⏳ **Coming Soon:**
- Topology graph construction
- Cost driver identification
- Risk assessment
- AI opportunity recommendations
- Executive report generation

### Advanced Usage

```bash
# Run tests to verify installation
pytest

# Run with coverage
pytest --cov=alip

# Format code (if contributing)
black .

# Lint code
ruff check .
```

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
# Check file permissions
chmod +x create_demo_data.py

# Check workspace permissions
ls -la workspace/
```

**Missing dependencies:**
```bash
# Reinstall all dependencies
pip install -r requirements.txt
```

### Getting Help

- Check [README.md](README.md) for detailed documentation
- Review [CONTRIBUTING.md](CONTRIBUTING.md) for development guide
- Open an issue for bugs or questions

---

## What's Next?

1. **Explore artifacts**: Review generated JSON and Markdown files
2. **Test with your data**: Try with real legacy system exports
3. **Wait for analysis**: Topology and cost analysis coming in Phase 2
4. **Provide feedback**: Help shape future features

---

**Ready to analyze your legacy systems! 🚀**
