# ALIP Deployment Guide

This guide covers deploying and running ALIP in production environments.

---

## Prerequisites

### System Requirements
- **OS:** Linux (Ubuntu 20.04+), macOS, or Windows WSL
- **Python:** 3.10 or higher
- **Memory:** 4GB RAM minimum (8GB recommended)
- **Disk:** 10GB free space minimum

### Access Requirements
- Read access to legacy systems (repositories, databases)
- Database export capabilities (pg_dump, mysqldump, etc.)
- Query log access
- Documentation files

---

## Installation

### Option 1: Development Setup

```bash
# Clone repository
git clone <repo-url>
cd alip

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"

# Verify installation
alip --version
pytest -q
```

### Option 2: Production Setup

```bash
# Clone repository
git clone <repo-url>
cd alip

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install production dependencies only
pip install -e .

# Verify installation
alip --version
```

### Option 3: Docker (Future)

```bash
# Build image
docker build -t alip:latest .

# Run container
docker run -it -v $(pwd)/workspace:/workspace alip:latest
```

---

## Configuration

### Environment Variables

Create `.env` file (optional, for LLM features):

```bash
# Optional: For AI-powered features (Phase 2)
ANTHROPIC_API_KEY=your-api-key-here

# Optional: Custom workspace location
ALIP_WORKSPACE_DIR=/path/to/workspace

# Optional: Locale
ALIP_DEFAULT_LOCALE=en
```

### Workspace Structure

```bash
# Default workspace location
workspace/
├── <engagement-id>/
│   ├── config/
│   │   └── engagement.json
│   ├── raw/          # Empty (no raw storage)
│   ├── processed/    # Normalized data
│   ├── artifacts/    # Generated artifacts
│   └── reports/      # Final reports
```

---

## Data Preparation

### Repository Export

```bash
# Option 1: Clone repository
git clone https://github.com/client/legacy-system.git /tmp/repo

# Option 2: Export specific branch
git archive --format=tar main | tar -xC /tmp/repo

# Option 3: Use existing directory
# Just provide path to code directory
```

### Database Schema Export

```bash
# PostgreSQL
pg_dump --schema-only --no-owner --no-privileges \
  -h localhost -U user -d dbname > schema.sql

# MySQL
mysqldump --no-data --skip-triggers \
  -h localhost -u user -p dbname > schema.sql

# Or export as JSON (recommended)
# Use your database management tool to export schema as JSON
```

### Query Log Export

```bash
# PostgreSQL: Enable logging in postgresql.conf
log_statement = 'all'
log_duration = on

# Extract recent logs
tail -n 10000 /var/log/postgresql/postgresql.log > queries.log

# Convert to JSON (manual or script)
# Format: [{"query": "...", "timestamp": "...", "duration_ms": 123}]
```

### Documentation Collection

```bash
# Gather all documentation
mkdir -p /tmp/docs

# Copy from various sources
cp -r /wiki/export/*.md /tmp/docs/
cp -r /confluence/exports/*.pdf /tmp/docs/
cp README*.md /tmp/docs/
cp ARCHITECTURE.md /tmp/docs/
```

---

## Running Analysis

### Step-by-Step Workflow

#### 1. Create Engagement

```bash
alip new \
  --name "Legacy ERP Analysis" \
  --id erp-2024-001 \
  --locale en
```

Output:
```
Creating new engagement: Legacy ERP Analysis (erp-2024-001)
✓ Workspace created: ./workspace/erp-2024-001
```

#### 2. Ingest Data

```bash
alip ingest \
  --engagement erp-2024-001 \
  --repo /tmp/legacy-repo \
  --db-schema /tmp/exports/schema.sql \
  --query-logs /tmp/logs/queries.json \
  --docs /tmp/documentation
```

Output:
```
Ingesting data for: Legacy ERP Analysis

→ Ingesting repository...
  ✓ Repository: 1,247 files

→ Ingesting database schema...
  ✓ Schema: 42 tables

→ Ingesting query logs...
  ✓ Queries: 10,000 logged

→ Ingesting documents...
  ✓ Documents: 15 files

✓ Ingestion complete
Artifacts saved to: workspace/erp-2024-001/artifacts
```

#### 3. Review Artifacts

```bash
# List generated artifacts
ls -lh workspace/erp-2024-001/artifacts/

# View summaries
cat workspace/erp-2024-001/artifacts/repo_inventory.md
cat workspace/erp-2024-001/artifacts/db_schema.md

# Review metrics
cat workspace/erp-2024-001/artifacts/repo_inventory_metrics.json
```

#### 4. Analysis (Phase 2)

```bash
# Not yet implemented
alip analyze --engagement erp-2024-001
```

#### 5. Generate Reports (Phase 2)

```bash
# Not yet implemented
alip report --engagement erp-2024-001 --format pdf
```

---

## Production Best Practices

### Security

#### 1. Credential Management
```bash
# NEVER commit credentials
echo ".env" >> .gitignore
echo "secrets/" >> .gitignore

# Use environment variables
export ANTHROPIC_API_KEY="$(cat /secure/api-key)"

# Or use secret management
aws secretsmanager get-secret-value --secret-id alip/api-key
```

#### 2. Data Redaction
```python
# Verify redaction is enabled
cat workspace/*/config/engagement.json | grep redaction_enabled
# Should show: "redaction_enabled": true
```

#### 3. Access Control
```bash
# Restrict workspace access
chmod 700 workspace/
chmod 600 workspace/*/config/engagement.json

# Use read-only database credentials
# Grant SELECT only, no INSERT/UPDATE/DELETE
```

### Data Isolation

```bash
# Separate workspace per engagement
workspace/
├── client-a-001/
├── client-b-002/
└── client-c-003/

# No cross-contamination
# Each engagement is isolated
```

### Backup & Recovery

```bash
# Backup workspace
tar -czf workspace-backup-$(date +%Y%m%d).tar.gz workspace/

# Backup to S3
aws s3 sync workspace/ s3://alip-backups/workspace/

# Restore
tar -xzf workspace-backup-20240101.tar.gz
```

---

## Monitoring

### Log Files

```bash
# Application logs (future)
tail -f logs/alip.log

# Error tracking
grep ERROR logs/alip.log

# Audit trail
cat workspace/*/artifacts/*_sources.json
```

### Metrics

```bash
# Engagement count
ls -1 workspace/ | wc -l

# Total artifacts
find workspace/ -name "*.json" | wc -l

# Disk usage
du -sh workspace/
```

---

## Troubleshooting

### Common Issues

#### 1. Import Errors

```bash
# Problem: ModuleNotFoundError
# Solution: Install dependencies
pip install -r requirements.txt

# Or reinstall package
pip install -e .
```

#### 2. Permission Denied

```bash
# Problem: Cannot create workspace
# Solution: Check permissions
mkdir -p workspace/
chmod 755 workspace/
```

#### 3. Memory Issues

```bash
# Problem: Out of memory during large repo scan
# Solution: Limit scan size
# Edit skills/repo.py - adjust max_files parameter
```

#### 4. Encoding Issues

```bash
# Problem: UnicodeDecodeError
# Solution: Files are read with error='ignore'
# This is already handled in the code
```

### Debug Mode

```bash
# Verbose output
alip ingest --engagement demo-001 --repo /path --verbose

# Python debug mode
PYTHONPATH=. python -m pdb cli.py ingest --engagement demo-001
```

---

## Performance Optimization

### Large Repositories

```python
# Adjust max_files in skills/repo.py
def scan_repo(path: Path, max_files: int = 50000):  # Increase limit
    # ...
```

### Query Log Limits

```python
# Limit queries parsed
alip ingest --engagement demo-001 \
  --query-logs /path/to/large.log
  # Automatically limits to 1000 queries
  # Edit skills/database.py to adjust
```

### Parallel Processing (Future)

```python
# Not yet implemented
# Will support multi-threaded ingestion in Phase 2
```

---

## Scaling Considerations

### Single Server (Current)
- ✅ MVP architecture
- ✅ 1-10 engagements
- ✅ Manual execution

### Multi-Server (Future)
- ⏳ Load balancing
- ⏳ Distributed processing
- ⏳ API server
- ⏳ Queue-based ingestion

---

## Integration Examples

### CI/CD Integration

```yaml
# .github/workflows/legacy-analysis.yml
name: Legacy System Analysis

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install ALIP
        run: pip install -e .
      - name: Run Analysis
        run: |
          alip new --name "Weekly Audit" --id "audit-$(date +%Y%m%d)"
          alip ingest --engagement "audit-$(date +%Y%m%d)" --repo .
```

### Cron Jobs

```bash
# /etc/cron.d/alip-weekly
0 0 * * 0 /opt/alip/bin/weekly-audit.sh

# weekly-audit.sh
#!/bin/bash
cd /opt/alip
source venv/bin/activate
alip new --name "Weekly Audit" --id "audit-$(date +%Y%m%d)"
alip ingest --engagement "audit-$(date +%Y%m%d)" \
  --repo /opt/legacy/code \
  --db-schema /opt/exports/schema.sql
```

---

## Disaster Recovery

### Backup Strategy

```bash
# Daily incremental backups
0 2 * * * /opt/alip/bin/backup-workspace.sh

# Weekly full backups
0 3 * * 0 /opt/alip/bin/full-backup.sh
```

### Recovery Procedure

```bash
# 1. Restore workspace
tar -xzf backup.tar.gz -C /

# 2. Verify integrity
alip list

# 3. Regenerate artifacts if needed
# (All artifacts are reproducible from sources)
```

---

## Support & Maintenance

### Regular Maintenance

```bash
# Weekly tasks
- Review disk usage
- Archive old engagements
- Update dependencies
- Review logs

# Monthly tasks
- Security updates
- Performance review
- Backup verification
```

### Version Updates

```bash
# Check current version
alip --version

# Update to latest
git pull
pip install -e . --upgrade
pytest -q  # Verify tests pass
```

---

## Contact & Resources

- **Documentation:** See README.md, QUICKSTART.md
- **Issues:** GitHub Issues (if applicable)
- **Security:** Report to security@company.com
- **Support:** support@company.com

---

**Safe Deployments! 🚀**
