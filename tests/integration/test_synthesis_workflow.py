"""Integration tests for SynthesisAgent in full workflow.

Tests the complete workflow:
1. Ingest repository, database schema, query logs, and documents
2. Build topology
3. Run cost analysis
4. Run risk analysis
5. Generate synthesis reports
6. Verify all output artifacts are generated
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
def sample_workspace(tmp_path: Path):
    """Create sample workspace with artifacts."""
    engagement_id = "test-synthesis-integration-001"
    workspace = init_workspace(
        engagement_id=engagement_id,
        client_name="Test Corp",
        base_dir=tmp_path,
        config_overrides={"read_only_mode": True, "state": "ingested"}
    )
    
    config = load_engagement_config(workspace)
    
    return workspace, config


@pytest.fixture
def sample_repo(tmp_path: Path):
    """Create sample repository."""
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    
    (repo / "main.py").write_text("""
import database

def get_user(email):
    return database.query("SELECT * FROM users WHERE email = ?", email)
""")
    
    return repo


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

CREATE INDEX idx_users_email ON users(email);
""")
    return schema


@pytest.fixture
def sample_query_logs(tmp_path: Path):
    """Create sample query log file."""
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
    ]
    
    with open(query_log, "w") as f:
        json.dump(queries, f)
    
    return query_log


@pytest.fixture
def sample_docs(tmp_path: Path):
    """Create sample documentation."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    
    (docs_dir / "README.md").write_text("""
# System README

For questions, contact John.
""")
    
    return docs_dir


def test_synthesis_full_workflow(
    sample_workspace,
    sample_repo,
    sample_schema,
    sample_query_logs,
    sample_docs
):
    """Test complete synthesis workflow."""
    workspace, config = sample_workspace
    
    # Step 1: Ingest all data
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
    
    # Step 5: Generate synthesis
    synthesis_agent = SynthesisAgent(workspace, config)
    synthesis_artifact = synthesis_agent.generate_executive_summary(
        topology_artifact=topology_artifact,
        cost_artifact=cost_artifact,
        risk_artifact=risk_artifact
    )
    
    # Step 6: Verify artifact structure
    assert synthesis_artifact.artifact_type == "synthesis"
    assert synthesis_artifact.engagement_id == config.engagement_id
    assert "executive_summary" in synthesis_artifact.data
    assert "technical_appendix" in synthesis_artifact.data
    assert "action_plan" in synthesis_artifact.data
    assert "metrics" in synthesis_artifact.data
    assert "recommendations" in synthesis_artifact.data


def test_synthesis_artifact_files(
    sample_workspace,
    sample_repo,
    sample_schema,
    sample_query_logs,
    sample_docs
):
    """Test that all synthesis artifact files are generated."""
    workspace, config = sample_workspace
    
    # Run full workflow
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
    synthesis_agent.generate_executive_summary(
        topology_artifact=topology_artifact,
        cost_artifact=cost_artifact,
        risk_artifact=risk_artifact
    )
    
    # Check all expected files exist
    expected_files = [
        "synthesis.json",
        "executive_summary.md",
        "technical_appendix.md",
        "action_plan.md",
        "synthesis_sources.json",
        "synthesis_metrics.json",
    ]
    
    for filename in expected_files:
        artifact_path = workspace.artifacts / filename
        assert artifact_path.exists(), f"Missing artifact: {filename}"


def test_synthesis_content_quality(
    sample_workspace,
    sample_repo,
    sample_schema,
    sample_query_logs,
    sample_docs
):
    """Test that generated reports have meaningful content."""
    workspace, config = sample_workspace
    
    # Run workflow
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
    synthesis_agent.generate_executive_summary(
        topology_artifact=topology_artifact,
        cost_artifact=cost_artifact,
        risk_artifact=risk_artifact
    )
    
    # Check executive summary
    exec_path = workspace.artifacts / "executive_summary.md"
    exec_content = exec_path.read_text()
    
    assert len(exec_content) > 500  # Substantial content
    assert "# Executive Summary" in exec_content
    assert config.client_name in exec_content
    assert "Executive Overview" in exec_content or "Key Findings" in exec_content
    
    # Check technical appendix
    tech_path = workspace.artifacts / "technical_appendix.md"
    tech_content = tech_path.read_text()
    
    assert len(tech_content) > 500
    assert "# Technical Appendix" in tech_content
    
    # Check action plan
    action_path = workspace.artifacts / "action_plan.md"
    action_content = action_path.read_text()
    
    assert len(action_content) > 200
    assert "# Action Plan" in action_content


def test_synthesis_metrics_calculation(
    sample_workspace,
    sample_repo,
    sample_schema,
    sample_query_logs,
    sample_docs
):
    """Test that synthesis correctly calculates and includes metrics."""
    workspace, config = sample_workspace
    
    # Run workflow
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
    
    # Verify metrics
    assert "metrics" in synthesis_artifact.data
    metrics = synthesis_artifact.data["metrics"]
    
    assert "total_components" in metrics
    assert "total_risks" in metrics
    assert "total_cost_ms" in metrics
    
    # Verify business value
    assert "business_value" in synthesis_artifact.data
    business_value = synthesis_artifact.data["business_value"]
    
    assert "cost_savings_potential_hours_per_day" in business_value
    assert "critical_risks_to_mitigate" in business_value


def test_synthesis_recommendations_prioritization(
    sample_workspace,
    sample_repo,
    sample_schema,
    sample_query_logs,
    sample_docs
):
    """Test that recommendations are properly prioritized."""
    workspace, config = sample_workspace
    
    # Run workflow
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
    
    # Verify recommendations
    recommendations = synthesis_artifact.data.get("recommendations", [])
    
    if len(recommendations) > 1:
        # Should be sorted by priority (descending)
        priorities = [r["priority"] for r in recommendations]
        assert priorities == sorted(priorities, reverse=True)
    
    # Verify structure
    for rec in recommendations:
        assert "priority" in rec
        assert "title" in rec
        assert "description" in rec
        assert "impact" in rec
        assert "effort" in rec

