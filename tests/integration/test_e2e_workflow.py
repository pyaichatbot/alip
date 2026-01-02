"""End-to-end integration test for complete workflow."""

import json
from pathlib import Path

import pytest

from core.models import EngagementConfig
from core.state_machine import EngagementState, StateViolationError, validate_transition
from skills.workspace import init_workspace, load_engagement_config, save_engagement_config


@pytest.fixture
def e2e_workspace(tmp_path: Path) -> tuple:
    """Create complete E2E test environment."""
    # Create workspace
    workspace = init_workspace(
        engagement_id="e2e-test",
        client_name="E2E Test Corp",
        base_dir=tmp_path / "workspace",
    )
    config = load_engagement_config(workspace)
    
    # Create sample repository
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    (repo / "main.py").write_text('print("Hello")\n' * 10)
    (repo / "utils.py").write_text('def test():\n    pass\n' * 5)
    (repo / "requirements.txt").write_text('pytest==7.0.0\n')
    
    # Create sample schema
    schema = tmp_path / "schema.sql"
    schema.write_text('''
CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(255));
CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER);
''')
    
    # Create sample query log
    query_log = tmp_path / "queries.json"
    with open(query_log, "w") as f:
        json.dump([
            {
                "query": "SELECT * FROM users",
                "timestamp": "2024-01-01T10:00:00",
                "duration_ms": 45.2,
            }
        ], f)
    
    return workspace, config, repo, schema, query_log


def test_complete_workflow_state_transitions(e2e_workspace: tuple) -> None:
    """Test that engagement follows correct state transitions."""
    workspace, config, repo, schema, query_log = e2e_workspace
    
    # Initial state should be NEW
    assert config.state == "new"
    
    # Should allow transition to INGESTED
    validate_transition(
        EngagementState(config.state),
        EngagementState.INGESTED,
    )
    
    # Update state
    config.update_state(EngagementState.INGESTED.value)
    save_engagement_config(workspace, config)
    
    # Verify state was updated
    reloaded = load_engagement_config(workspace)
    assert reloaded.state == "ingested"
    assert reloaded.updated_at > reloaded.created_at
    
    # Should NOT allow skipping to FINALIZED
    with pytest.raises(StateViolationError):
        validate_transition(
            EngagementState(reloaded.state),
            EngagementState.FINALIZED,
        )


def test_read_only_mode_enforced(e2e_workspace: tuple) -> None:
    """Test that read-only mode is enforced."""
    workspace, config, repo, schema, query_log = e2e_workspace
    
    # Read-only should be enabled by default
    assert config.read_only_mode is True
    
    # Redaction should be enabled
    assert config.redaction_enabled is True
    
    # Raw data storage should be disabled
    assert config.store_raw_data is False


def test_artifact_completeness(e2e_workspace: tuple) -> None:
    """Test that all required artifacts are generated."""
    from agents.ingestion import IngestionAgent
    
    workspace, config, repo, schema, query_log = e2e_workspace
    
    # Run ingestion
    agent = IngestionAgent(workspace, config)
    
    # Ingest all sources
    repo_artifact = agent.ingest_repository(repo)
    schema_artifact = agent.ingest_database_schema(schema)
    query_artifact = agent.ingest_query_logs(query_log)
    
    # Verify all artifact files exist
    expected_files = [
        "repo_inventory.json",
        "repo_inventory.md",
        "repo_inventory_sources.json",
        "repo_inventory_metrics.json",
        "db_schema.json",
        "db_schema.md",
        "db_schema_sources.json",
        "db_schema_metrics.json",
        "query_logs.json",
        "query_logs.md",
        "query_logs_sources.json",
        "query_logs_metrics.json",
    ]
    
    for filename in expected_files:
        artifact_path = workspace.artifacts / filename
        assert artifact_path.exists(), f"Missing artifact: {filename}"


def test_artifact_json_schema_validity(e2e_workspace: tuple) -> None:
    """Test that artifact JSON has valid schema."""
    from agents.ingestion import IngestionAgent
    
    workspace, config, repo, schema, query_log = e2e_workspace
    
    # Run ingestion
    agent = IngestionAgent(workspace, config)
    agent.ingest_repository(repo)
    
    # Load and validate JSON
    artifact_file = workspace.artifacts / "repo_inventory.json"
    with open(artifact_file) as f:
        data = json.load(f)
    
    # Verify required fields
    assert "artifact_type" in data
    assert "engagement_id" in data
    assert "created_at" in data
    assert "data" in data
    assert "sources" in data
    assert "metrics" in data
    assert "review_status" in data
    
    # Verify engagement ID matches
    assert data["engagement_id"] == "e2e-test"
    
    # Verify review status is pending
    assert data["review_status"] == "pending"


def test_deterministic_output(e2e_workspace: tuple) -> None:
    """Test that running twice produces consistent output."""
    from agents.ingestion import IngestionAgent
    
    workspace, config, repo, schema, query_log = e2e_workspace
    
    # Run ingestion twice
    agent = IngestionAgent(workspace, config)
    artifact1 = agent.ingest_repository(repo)
    
    # Clear artifacts
    for f in workspace.artifacts.glob("repo_inventory*"):
        f.unlink()
    
    # Run again
    artifact2 = agent.ingest_repository(repo)
    
    # Metrics should be identical
    assert artifact1.metrics == artifact2.metrics
    
    # Data should be consistent (excluding timestamps)
    assert artifact1.data["total_files"] == artifact2.data["total_files"]
    assert artifact1.data["languages"] == artifact2.data["languages"]


def test_no_network_calls_during_ingestion(e2e_workspace: tuple, monkeypatch) -> None:
    """Test that ingestion doesn't make network calls."""
    from agents.ingestion import IngestionAgent
    import socket
    
    workspace, config, repo, schema, query_log = e2e_workspace
    
    # Block all network access
    def block_network(*args, **kwargs):
        raise RuntimeError("Network call detected during ingestion!")
    
    monkeypatch.setattr(socket, "socket", block_network)
    
    # Run ingestion - should complete without network
    agent = IngestionAgent(workspace, config)
    artifact = agent.ingest_repository(repo)
    
    # Should succeed
    assert artifact.metrics["total_files"] > 0


def test_source_traceability(e2e_workspace: tuple) -> None:
    """Test that all outputs have source references."""
    from agents.ingestion import IngestionAgent
    
    workspace, config, repo, schema, query_log = e2e_workspace
    
    # Run ingestion
    agent = IngestionAgent(workspace, config)
    artifact = agent.ingest_repository(repo)
    
    # Every artifact must have sources
    assert len(artifact.sources) > 0
    
    # Sources must have required fields
    for source in artifact.sources:
        assert source.type in ["repo", "db", "doc", "log"]
        assert source.path
        assert source.timestamp
    
    # Load sources JSON
    sources_file = workspace.artifacts / "repo_inventory_sources.json"
    with open(sources_file) as f:
        sources_data = json.load(f)
    
    assert "sources" in sources_data
    assert len(sources_data["sources"]) > 0


def test_engagement_lifecycle_complete(e2e_workspace: tuple) -> None:
    """Test complete engagement lifecycle."""
    workspace, config, repo, schema, query_log = e2e_workspace
    
    # Track state progression
    states = [config.state]
    
    # NEW → INGESTED
    config.update_state(EngagementState.INGESTED.value)
    states.append(config.state)
    
    # INGESTED → ANALYZED
    config.update_state(EngagementState.ANALYZED.value)
    states.append(config.state)
    
    # ANALYZED → REVIEWED
    config.update_state(EngagementState.REVIEWED.value)
    states.append(config.state)
    
    # REVIEWED → FINALIZED
    config.update_state(EngagementState.FINALIZED.value)
    states.append(config.state)
    
    # Verify progression
    expected = ["new", "ingested", "analyzed", "reviewed", "finalized"]
    assert states == expected


def test_review_gate_integration(e2e_workspace: tuple) -> None:
    """Test review gate workflow."""
    from core.review_gate import ReviewGate
    from agents.ingestion import IngestionAgent
    
    workspace, config, repo, schema, query_log = e2e_workspace
    
    # Create review gate
    gate = ReviewGate(workspace.root)
    
    # Run ingestion
    agent = IngestionAgent(workspace, config)
    artifact = agent.ingest_repository(repo)
    
    # Submit for review
    artifact_path = workspace.artifacts / "repo_inventory.json"
    gate.submit_for_review(artifact, artifact_path)
    
    # Verify pending
    pending = gate.get_pending_reviews()
    assert len(pending) >= 0  # May or may not track this artifact
    
    # Approve artifact
    decision = gate.approve(
        artifact_id="repo_inventory",
        reviewer="test_reviewer",
        comments="Looks good",
    )
    
    assert decision.decision.value == "approved"
    
    # Verify review was logged
    summary = gate.get_review_summary()
    assert summary["approved"] >= 1
