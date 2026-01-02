# ALIP - Project Index

**AI-Assisted Legacy Intelligence Platform**  
**Version:** 0.1.0 (MVP Build-Ready)

---

## 📋 Quick Navigation

### Getting Started
1. **[README.md](README.md)** - Start here for project overview
2. **[QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
3. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Comprehensive project overview

### For Developers
4. **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development guidelines
5. **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Production deployment
6. **[CHANGELOG.md](CHANGELOG.md)** - Version history

### Product Documentation
7. **[PRD_AI_Assisted_Legacy_Intelligence_Core.txt](../PRD_AI_Assisted_Legacy_Intelligence_Core.txt)** - Core requirements
8. **Market Addendums:** Germany, USA, India - See `/mnt/project/`

---

## 🎯 What is ALIP?

ALIP provides **read-only AI-assisted intelligence** for legacy systems:

- ✅ **Safe:** Read-only by design, no system modifications
- ✅ **Traceable:** Full source attribution for all insights
- ✅ **Intelligent:** AI-powered analysis (Phase 2)
- ✅ **Human-Controlled:** Review gates for all outputs

**Target Market:** Mid-sized enterprises (50-500 employees) with poorly documented legacy systems.

---

## 🚀 Quick Start (3 Commands)

```bash
# 1. Generate demo data
python create_demo_data.py

# 2. Create engagement & ingest
alip new --name "Demo Corp" --id demo-001
alip ingest --engagement demo-001 \
  --repo demo_data/sample_repo \
  --db-schema demo_data/schema.sql \
  --query-logs demo_data/queries.json \
  --docs demo_data/docs

# 3. View results
ls workspace/demo-001/artifacts/
```

---

## 📁 Project Structure

```
alip/
├── README.md              ← Start here
├── QUICKSTART.md          ← 5-minute guide
├── PROJECT_SUMMARY.md     ← Complete overview
├── CONTRIBUTING.md        ← Dev guidelines
├── DEPLOYMENT_GUIDE.md    ← Production setup
├── CHANGELOG.md           ← Version history
│
├── core/                  ← Core infrastructure
│   ├── models.py          → Data models (Pydantic)
│   ├── utils.py           → Utilities & redaction
│   └── llm/client.py      → LLM abstraction
│
├── agents/                ← Analysis agents
│   └── ingestion.py       → IngestionAgent ✅
│
├── skills/                ← Reusable functions
│   ├── workspace.py       → Workspace management ✅
│   ├── repo.py            → Repository analysis ✅
│   ├── database.py        → DB schema & queries ✅
│   └── documents.py       → Document ingestion ✅
│
├── tests/                 ← Test suite (>80% coverage)
│   ├── unit/              → Unit tests ✅
│   └── integration/       → Integration tests ✅
│
├── cli.py                 ← Command-line interface ✅
├── create_demo_data.py    ← Demo generator ✅
│
├── pyproject.toml         ← Package config
├── requirements.txt       ← Dependencies
├── Makefile              ← Common tasks
└── .gitignore            ← Git exclusions
```

---

## ✅ Implemented (MVP v0.1.0)

### Core Infrastructure
- [x] Pydantic data models
- [x] Workspace management
- [x] Configuration system
- [x] LLM client abstraction

### Data Ingestion
- [x] Repository scanning (15+ languages)
- [x] Database schema parsing (JSON/SQL)
- [x] Query log analysis
- [x] Document ingestion (PDF/DOCX/MD/TXT)

### Safety & Compliance
- [x] Read-only mode enforcement
- [x] Automatic redaction
- [x] Source tracking
- [x] No raw data storage

### Developer Experience
- [x] CLI interface
- [x] Rich terminal output
- [x] Comprehensive tests
- [x] Complete documentation
- [x] Demo system

---

## ⏳ Coming Soon (Phase 2)

### Analysis Agents
- [ ] TopologyAgent - Dependency graphs
- [ ] CostAnalysisAgent - Cost drivers
- [ ] RiskAnalysisAgent - Risk assessment
- [ ] OpportunityAgent - AI recommendations
- [ ] SynthesisAgent - Executive summaries

### Advanced Features
- [ ] PDF report generation
- [ ] LLM-powered insights
- [ ] Continuous monitoring
- [ ] Change impact simulation

---

## 📊 Key Statistics

- **Lines of Code:** ~3,500
- **Test Coverage:** >80% target
- **Languages Detected:** 15+
- **Document Formats:** 4 (PDF, DOCX, MD, TXT)
- **CLI Commands:** 5
- **Test Cases:** 40+
- **Documentation Pages:** 6

---

## 🛠️ Common Tasks

### Installation
```bash
pip install -e ".[dev]"
```

### Run Tests
```bash
make test
# or
pytest -v
```

### Create Demo
```bash
make demo
# or
python create_demo_data.py
```

### Format Code
```bash
make format
# or
black .
```

### Run Full Demo
```bash
make run-demo
```

---

## 📖 Documentation Map

| Document | Purpose | Audience |
|----------|---------|----------|
| **README.md** | Project overview & architecture | Everyone |
| **QUICKSTART.md** | Get started in 5 minutes | New users |
| **PROJECT_SUMMARY.md** | Comprehensive technical overview | Developers |
| **CONTRIBUTING.md** | Development guidelines | Contributors |
| **DEPLOYMENT_GUIDE.md** | Production deployment | Ops/DevOps |
| **CHANGELOG.md** | Version history | Everyone |

---

## 🔐 Security & Compliance

### Read-Only Guarantee
- No write operations to client systems
- Database connections are SELECT-only
- Repository access is clone-based only

### Data Redaction
Automatically redacts:
- Email addresses
- API keys and tokens
- Passwords
- AWS credentials
- Custom patterns (configurable)

### Audit Trail
Every artifact includes:
- Source references
- Timestamps
- Review status
- Confidence levels

---

## 🌍 Market Positioning

### Germany (DACH)
- **Focus:** Compliance, documentation, explainability
- **Key:** GDPR strict mode, EU AI Act alignment

### USA
- **Focus:** ROI, speed, measurable outcomes
- **Key:** Fast pilots, quantified savings

### India
- **Focus:** Cost reduction, automation
- **Key:** Documentation generation, efficiency

---

## 🧪 Testing

### Run All Tests
```bash
pytest -v
```

### With Coverage
```bash
pytest --cov=alip --cov-report=term-missing
```

### Specific Test
```bash
pytest tests/unit/test_workspace.py -v
```

---

## 📦 Dependencies

### Core
- pydantic>=2.0.0 - Data validation
- click>=8.1.0 - CLI framework
- rich>=13.0.0 - Terminal formatting

### Analysis
- gitpython>=3.1.0 - Git operations
- sqlparse>=0.4.0 - SQL parsing
- PyPDF2>=3.0.0 - PDF extraction

### Development
- pytest>=7.0.0 - Testing
- black>=23.0.0 - Formatting
- ruff>=0.1.0 - Linting

---

## 🤝 Contributing

1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Fork repository
3. Create feature branch
4. Write tests
5. Submit PR

---

## 📝 License

Proprietary - All Rights Reserved

---

## 🔗 Quick Links

- **Start Here:** [README.md](README.md)
- **Quick Start:** [QUICKSTART.md](QUICKSTART.md)
- **Full Docs:** [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
- **Dev Guide:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Deploy:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## 💬 Support

- Open an issue for bugs
- Start a discussion for questions
- Contact maintainers for urgent matters

---

**Built with safety, transparency, and trust at the core.** 🚀

Last Updated: 2024-01-01  
Version: 0.1.0 (MVP)
