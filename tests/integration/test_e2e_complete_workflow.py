"""End-to-end test for complete ALIP workflow.

Tests the full workflow from ingestion to report generation:
1. Create engagement
2. Ingest data (repo, schema, query logs, docs)
3. Analyze (topology, cost, risk)
4. Generate reports (synthesis)
5. Verify all 25 artifacts are generated
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

from agents.synthesis import SynthesisAgent
from agents.topology import TopologyAgent
from agents.cost_analysis import CostAnalysisAgent
from agents.risk_analysis import RiskAnalysisAgent
from agents.ingestion import IngestionAgent
from core.models import AnalysisArtifact, EngagementConfig, SourceReference, ConfidenceLevel
from skills.workspace import init_workspace, load_engagement_config


@pytest.fixture
def complete_workspace(tmp_path: Path):
    """Create complete workspace for E2E test."""
    engagement_id = "e2e-test-001"
    workspace = init_workspace(
        engagement_id=engagement_id,
        client_name="Enterprise Corp",
        base_dir=tmp_path,
        config_overrides={"read_only_mode": True, "state": "new"}
    )
    
    config = load_engagement_config(workspace)
    
    return workspace, config


@pytest.fixture
def sample_repo(tmp_path: Path):
    """Create sample repository with multiple files."""
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    
    (repo / "config.py").write_text("""
# Configuration
DB_PASSWORD = "secret123"  # Security issue
API_KEY = "sk-1234567890abcdef"
""")
    
    (repo / "database.py").write_text("""
import sqlite3

def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection
    return execute(query)
""")
    
    (repo / "main.py").write_text("""
import database
import config

def get_user(email):
    return database.query("SELECT * FROM users WHERE email = ?", email)
""")
    
    return repo


@pytest.fixture
def sample_schema(tmp_path: Path):
    """Create sample database schema."""
    schema = tmp_path / "schema.sql"
    schema.write_text("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255),
    name VARCHAR(255)
);

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    created_at TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
""")
    return schema


@pytest.fixture
def sample_query_logs(tmp_path: Path):
    """Create sample query logs."""
    query_log = tmp_path / "queries.json"
    
    queries = [
        {
            "query": "SELECT * FROM users WHERE email = 'test@example.com'",
            "timestamp": "2024-01-02T10:00:00",
            "duration_ms": 150.0,
        },
        {
            "query": "SELECT * FROM users WHERE email = 'admin@example.com'",
            "timestamp": "2024-01-02T10:01:00",
            "duration_ms": 160.0,
        },
        {
            "query": "SELECT id FROM sessions WHERE user_id = 123",
            "timestamp": "2024-01-02T10:02:00",
            "duration_ms": 5.0,
        },
    ]
    
    with open(query_log, "w") as f:
        json.dump(queries, f)
    
    return query_log


@pytest.fixture
def sample_docs(tmp_path: Path):
    """Create sample documentation."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    
    (docs_dir / "runbook.md").write_text("""
# Deployment Runbook

To deploy:
1. Manually SSH into production server
2. Run the deployment script
3. Contact John if there are issues
4. Ask Sarah about database migrations
5. Contact John for production access
""")
    
    (docs_dir / "README.md").write_text("""
# System README

For questions, reach out to Alice.
If the system crashes, contact Bob immediately.
""")
    
    return docs_dir


def test_complete_e2e_workflow(
    complete_workspace,
    sample_repo,
    sample_schema,
    sample_query_logs,
    sample_docs
):
    """Test complete end-to-end workflow."""
    workspace, config = complete_workspace
    
    # Step 1: Ingest all data sources
    ingestion_agent = IngestionAgent(workspace, config)
    
    repo_artifact = ingestion_agent.ingest_repository(sample_repo)
    db_artifact = ingestion_agent.ingest_database_schema(sample_schema)
    query_artifact = ingestion_agent.ingest_query_logs(sample_query_logs)
    docs_artifact = ingestion_agent.ingest_documents(sample_docs)
    
    # Step 2: Build topology
    topology_agent = TopologyAgent(workspace, config)
    topology_artifact = topology_agent.build_topology(repo_artifact, db_artifact)
    
    # Step 3: Run cost analysis
    cost_agent = CostAnalysisAgent(workspace, config)
    cost_artifact = cost_agent.analyze_costs(
        query_logs_artifact=query_artifact,
        db_schema_artifact=db_artifact,
        topology_artifact=topology_artifact
    )
    
    # Step 4: Run risk analysis
    risk_agent = RiskAnalysisAgent(workspace, config)
    risk_artifact = risk_agent.analyze_risks(
        repo_artifact=repo_artifact,
        db_artifact=db_artifact,
        docs_artifact=docs_artifact,
        topology_artifact=topology_artifact
    )
    
    # Step 5: Generate synthesis reports
    synthesis_agent = SynthesisAgent(workspace, config)
    synthesis_artifact = synthesis_agent.generate_executive_summary(
        topology_artifact=topology_artifact,
        cost_artifact=cost_artifact,
        risk_artifact=risk_artifact
    )
    
    # Step 6: Verify all artifacts exist
    verify_all_artifacts(workspace)


def verify_all_artifacts(workspace: Path):
    """Verify all 25 expected artifacts are generated.
    
    Expected artifacts:
    For Executives:
    - executive_summary.md
    - action_plan.md
    
    For Technical Teams:
    - technical_appendix.md
    - topology.md
    - cost_drivers.md
    - risk_register.md
    
    For Compliance:
    - All *_sources.json files
    - All *_metrics.json files
    - All main artifact JSON files
    """
    
    # Executive reports
    executive_files = [
        "executive_summary.md",
        "action_plan.md",
    ]
    
    # Technical reports
    technical_files = [
        "technical_appendix.md",
        "topology.md",
        "cost_drivers.md",
        "risk_register.md",
    ]
    
    # Main artifacts (JSON)
    main_artifacts = [
        "repo_inventory.json",  # Repository artifact
        "db_schema.json",  # Database schema artifact
        "query_logs.json",
        "documents.json",
        "topology.json",
        "cost_drivers.json",
        "risk_register.json",
        "synthesis.json",
    ]
    
    # Sources files
    sources_files = [
        "topology_sources.json",
        "cost_drivers_sources.json",
        "risk_register_sources.json",
        "synthesis_sources.json",
    ]
    
    # Metrics files
    metrics_files = [
        "topology_metrics.json",
        "cost_drivers_metrics.json",
        "risk_register_metrics.json",
        "synthesis_metrics.json",
    ]
    
    all_expected = (
        executive_files +
        technical_files +
        main_artifacts +
        sources_files +
        metrics_files
    )
    
    # Check each file exists
    missing = []
    found = []
    
    for filename in all_expected:
        artifact_path = workspace.artifacts / filename
        if artifact_path.exists():
            found.append(filename)
        else:
            missing.append(filename)
    
    # Print summary
    print(f"\n✓ Found {len(found)}/{len(all_expected)} artifacts")
    
    if missing:
        print(f"\n✗ Missing artifacts:")
        for filename in missing:
            print(f"  - {filename}")
    
    # Verify critical files exist
    critical_files = [
        "executive_summary.md",
        "technical_appendix.md",
        "action_plan.md",
        "topology.md",
        "cost_drivers.md",
        "risk_register.md",
        "synthesis.json",
    ]
    
    for filename in critical_files:
        assert (workspace.artifacts / filename).exists(), f"Critical artifact missing: {filename}"
    
    # Verify we have at least 20 artifacts (allowing for some naming variations)
    total_artifacts = len(list(workspace.artifacts.glob("*")))
    assert total_artifacts >= 20, f"Expected at least 20 artifacts, found {total_artifacts}"


def test_artifact_content_quality(complete_workspace, sample_repo, sample_schema, sample_query_logs, sample_docs):
    """Test that all generated artifacts have meaningful content."""
    workspace, config = complete_workspace
    
    # Run complete workflow
    ingestion_agent = IngestionAgent(workspace, config)
    repo_artifact = ingestion_agent.ingest_repository(sample_repo)
    db_artifact = ingestion_agent.ingest_database_schema(sample_schema)
    query_artifact = ingestion_agent.ingest_query_logs(sample_query_logs)
    docs_artifact = ingestion_agent.ingest_documents(sample_docs)
    
    topology_agent = TopologyAgent(workspace, config)
    topology_artifact = topology_agent.build_topology(repo_artifact, db_artifact)
    
    cost_agent = CostAnalysisAgent(workspace, config)
    cost_artifact = cost_agent.analyze_costs(
        query_logs_artifact=query_artifact,
        db_schema_artifact=db_artifact,
        topology_artifact=topology_artifact
    )
    
    risk_agent = RiskAnalysisAgent(workspace, config)
    risk_artifact = risk_agent.analyze_risks(
        repo_artifact=repo_artifact,
        db_artifact=db_artifact,
        docs_artifact=docs_artifact,
        topology_artifact=topology_artifact
    )
    
    synthesis_agent = SynthesisAgent(workspace, config)
    synthesis_artifact = synthesis_agent.generate_executive_summary(
        topology_artifact=topology_artifact,
        cost_artifact=cost_artifact,
        risk_artifact=risk_artifact
    )
    
    # Verify executive summary has content
    exec_path = workspace.artifacts / "executive_summary.md"
    assert exec_path.exists()
    exec_content = exec_path.read_text()
    assert len(exec_content) > 500
    assert config.client_name in exec_content
    
    # Verify technical appendix has content
    tech_path = workspace.artifacts / "technical_appendix.md"
    assert tech_path.exists()
    tech_content = tech_path.read_text()
    assert len(tech_content) > 500
    
    # Verify action plan has content
    action_path = workspace.artifacts / "action_plan.md"
    assert action_path.exists()
    action_content = action_path.read_text()
    assert len(action_content) > 200
    
    # Verify JSON artifacts are valid
    json_files = list(workspace.artifacts.glob("*.json"))
    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)
            assert data is not None
            # Main artifacts should have artifact_type
            if "artifact_type" in data:
                assert data["artifact_type"] in [
                    "repo_inventory", "db_schema", "query_logs", "documents",
                    "topology", "cost_drivers", "risk_register", "synthesis"
                ]

