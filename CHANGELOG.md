# Changelog

All notable changes to ALIP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Topology graph construction
- Cost driver analysis
- Risk assessment (SPOFs, tribal knowledge)
- AI opportunity identification
- Executive report generation
- PDF output support

## [0.1.0] - 2024-01-01

### Added
- Initial MVP release
- Workspace management with engagement tracking
- CLI interface (`alip` command)
- Data ingestion for multiple source types:
  - Repository scanning with language detection
  - Database schema parsing (JSON and SQL DDL)
  - Query log analysis with cost metrics
  - Document ingestion (PDF, DOCX, Markdown, TXT)
- IngestionAgent for coordinated data collection
- Automatic redaction of sensitive information:
  - Email addresses
  - API keys and tokens
  - Passwords
  - AWS credentials
- Source reference tracking for all artifacts
- Structured artifact generation (JSON + Markdown)
- Comprehensive test suite with >80% coverage:
  - Unit tests for all skills
  - Integration tests for workflows
- Documentation:
  - README with architecture overview
  - QUICKSTART guide
  - CONTRIBUTING guidelines
  - Demo data generator
- Safety guarantees:
  - Read-only mode enforcement
  - No raw data storage
  - Human-in-the-loop review gates
  - Audit trail for all operations

### Core Skills
- `workspace.py` - Workspace initialization and management
- `repo.py` - Repository scanning and analysis
- `database.py` - Schema parsing and query log analysis
- `documents.py` - Multi-format document ingestion
- `utils.py` - Redaction, hashing, artifact saving

### Architecture
- Modular agent-based design
- Vendor-agnostic LLM client abstraction
- Pydantic models for type safety
- Clean separation of concerns:
  - `core/` - Shared models and utilities
  - `agents/` - Analysis agents
  - `skills/` - Reusable functions
  - `tests/` - Comprehensive test coverage

### Developer Experience
- Type hints throughout
- Comprehensive docstrings
- Black code formatting
- Ruff linting
- pytest test framework
- Rich CLI output with colors and tables

### Configuration
- Per-engagement configuration files
- Locale support (en, de)
- Configurable redaction patterns
- Output format selection

### Known Limitations
- MVP phase - analysis agents not yet implemented
- No PDF report generation yet
- No continuous monitoring
- Single-user (no multi-tenancy)
- Offline only (no API server)

## [0.0.1] - 2023-12-15

### Added
- Project structure
- Basic documentation
- PRD and requirements gathering
