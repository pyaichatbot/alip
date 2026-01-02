"""Integration tests for CostAnalysisAgent in full workflow.

Tests the complete workflow:
1. Ingest repository, database schema, and query logs
2. Build topology
3. Run cost analysis
4. Verify artifacts are generated correctly
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

from agents.cost_analysis import CostAnalysisAgent
from agents.topology import TopologyAgent
from agents.ingestion import IngestionAgent
from core.models import AnalysisArtifact, EngagementConfig, SourceReference, ConfidenceLevel
from skills.workspace import init_workspace, load_engagement_config


@pytest.fixture
def sample_workspace(tmp_path: Path):
    """Create sample workspace with artifacts."""
    engagement_id = "test-cost-integration-001"
    workspace = init_workspace(
        engagement_id=engagement_id,
        client_name="Test Corp",
        base_dir=tmp_path,
        config_overrides={"read_only_mode": True, "state": "ingested"}
    )
    
    config = load_engagement_config(workspace)
    
    return workspace, config


@pytest.fixture
def sample_query_logs(tmp_path: Path):
    """Create sample query log file."""
    query_log = tmp_path / "queries.json"
    
    # Create realistic query log with slow and frequent queries
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
            "query": "SELECT * FROM users WHERE email = 'user@example.com'",
            "timestamp": "2024-01-02T10:02:00",
            "duration_ms": 145.0,
        },
        # Frequent but fast query
        {
            "query": "SELECT id FROM sessions WHERE user_id = 123",
            "timestamp": "2024-01-02T10:03:00",
            "duration_ms": 5.0,
        },
        {
            "query": "SELECT id FROM sessions WHERE user_id = 456",
            "timestamp": "2024-01-02T10:04:00",
            "duration_ms": 6.0,
        },
        {
            "query": "SELECT id FROM sessions WHERE user_id = 789",
            "timestamp": "2024-01-02T10:05:00",
            "duration_ms": 5.5,
        },
    ]
    
    with open(query_log, "w") as f:
        json.dump(queries, f)
    
    return query_log


@pytest.fixture
def sample_schema(tmp_path: Path):
    """Create sample database schema file."""
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
def sample_repo(tmp_path: Path):
    """Create sample repository."""
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    
    (repo / "main.py").write_text("""
import database

def get_user(email):
    return database.query("SELECT * FROM users WHERE email = ?", email)

def get_session(user_id):
    return database.query("SELECT id FROM sessions WHERE user_id = ?", user_id)
""")
    
    return repo


def test_cost_analysis_integration(
    sample_workspace,
    sample_repo,
    sample_schema,
    sample_query_logs
):
    """Test full cost analysis workflow."""
    workspace, config = sample_workspace
    
    # Step 1: Ingest data
    ingestion_agent = IngestionAgent(workspace, config)
    
    repo_artifact = ingestion_agent.ingest_repository(sample_repo)
    db_artifact = ingestion_agent.ingest_database_schema(sample_schema)
    query_artifact = ingestion_agent.ingest_query_logs(sample_query_logs)
    
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
    
    # Step 4: Verify artifact structure
    assert cost_artifact.artifact_type == "cost_drivers"
    assert cost_artifact.engagement_id == config.engagement_id
    assert "cost_drivers" in cost_artifact.data
    assert "summary" in cost_artifact.data
    
    # Step 5: Verify cost drivers were identified
    cost_drivers = cost_artifact.data["cost_drivers"]
    assert len(cost_drivers) > 0
    
    # Step 6: Verify summary statistics
    summary = cost_artifact.data["summary"]
    assert summary["total_queries_analyzed"] > 0
    assert summary["unique_query_patterns"] > 0
    
    # Step 7: Verify artifacts were saved
    cost_json = workspace.artifacts / "cost_drivers.json"
    assert cost_json.exists()
    
    cost_md = workspace.artifacts / "cost_drivers.md"
    assert cost_md.exists()
    
    # Step 8: Verify markdown content
    md_content = cost_md.read_text()
    assert "Cost Analysis Report" in md_content
    assert "Summary" in md_content


def test_cost_analysis_without_query_logs(
    sample_workspace,
    sample_repo,
    sample_schema
):
    """Test cost analysis gracefully handles missing query logs."""
    workspace, config = sample_workspace
    
    # Ingest without query logs
    ingestion_agent = IngestionAgent(workspace, config)
    repo_artifact = ingestion_agent.ingest_repository(sample_repo)
    db_artifact = ingestion_agent.ingest_database_schema(sample_schema)
    
    # Build topology
    topology_agent = TopologyAgent(workspace, config)
    topology_artifact = topology_agent.build_topology(repo_artifact, db_artifact)
    
    # Run cost analysis without query logs
    cost_agent = CostAnalysisAgent(workspace, config)
    cost_artifact = cost_agent.analyze_costs(
        query_logs_artifact=None,
        db_schema_artifact=db_artifact,
        topology_artifact=topology_artifact
    )
    
    # Should create minimal artifact
    assert cost_artifact.artifact_type == "cost_drivers"
    assert len(cost_artifact.data["cost_drivers"]) == 0
    assert "note" in cost_artifact.data
    assert cost_artifact.confidence == ConfidenceLevel.LOW


def test_cost_analysis_artifact_completeness(
    sample_workspace,
    sample_repo,
    sample_schema,
    sample_query_logs
):
    """Test that all cost analysis artifacts are generated."""
    workspace, config = sample_workspace
    
    # Run full workflow
    ingestion_agent = IngestionAgent(workspace, config)
    repo_artifact = ingestion_agent.ingest_repository(sample_repo)
    db_artifact = ingestion_agent.ingest_database_schema(sample_schema)
    query_artifact = ingestion_agent.ingest_query_logs(sample_query_logs)
    
    topology_agent = TopologyAgent(workspace, config)
    topology_artifact = topology_agent.build_topology(repo_artifact, db_artifact)
    
    cost_agent = CostAnalysisAgent(workspace, config)
    cost_artifact = cost_agent.analyze_costs(
        query_logs_artifact=query_artifact,
        db_schema_artifact=db_artifact,
        topology_artifact=topology_artifact
    )
    
    # Check all artifact files exist
    expected_files = [
        "cost_drivers.json",
        "cost_drivers.md",
        "cost_drivers_sources.json",
        "cost_drivers_metrics.json",
    ]
    
    for filename in expected_files:
        artifact_path = workspace.artifacts / filename
        assert artifact_path.exists(), f"Missing artifact: {filename}"
    
    # Verify JSON structure
    with open(workspace.artifacts / "cost_drivers.json") as f:
        data = json.load(f)
        assert "artifact_type" in data
        assert "data" in data
        assert "sources" in data
        assert "metrics" in data


def test_cost_analysis_source_traceability(
    sample_workspace,
    sample_repo,
    sample_schema,
    sample_query_logs
):
    """Test that cost analysis artifacts have proper source references."""
    workspace, config = sample_workspace
    
    # Run workflow
    ingestion_agent = IngestionAgent(workspace, config)
    repo_artifact = ingestion_agent.ingest_repository(sample_repo)
    db_artifact = ingestion_agent.ingest_database_schema(sample_schema)
    query_artifact = ingestion_agent.ingest_query_logs(sample_query_logs)
    
    topology_agent = TopologyAgent(workspace, config)
    topology_artifact = topology_agent.build_topology(repo_artifact, db_artifact)
    
    cost_agent = CostAnalysisAgent(workspace, config)
    cost_artifact = cost_agent.analyze_costs(
        query_logs_artifact=query_artifact,
        db_schema_artifact=db_artifact,
        topology_artifact=topology_artifact
    )
    
    # Verify sources
    assert len(cost_artifact.sources) > 0
    
    for source in cost_artifact.sources:
        assert source.type in ["query_logs", "db_schema", "topology"]
        assert source.path
        assert source.timestamp

