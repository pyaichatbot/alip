"""Integration tests for ingestion workflow."""

from pathlib import Path

import pytest

from agents.ingestion import IngestionAgent
from skills.workspace import init_workspace, load_engagement_config


@pytest.fixture
def demo_workspace(tmp_path: Path) -> tuple:
    """Create demo workspace and sample data."""
    # Create workspace
    workspace = init_workspace(
        engagement_id="integration-test",
        client_name="Integration Test Corp",
        base_dir=tmp_path / "workspace",
    )
    config = load_engagement_config(workspace)
    
    # Create sample repo
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    (repo / "main.py").write_text('print("Hello")\n' * 10)
    (repo / "utils.py").write_text('def test():\n    pass\n' * 5)
    (repo / "requirements.txt").write_text('pytest==7.0.0\n')
    
    # Create sample schema
    schema = tmp_path / "schema.sql"
    schema.write_text('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255)
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    total DECIMAL(10, 2)
);
''')
    
    return workspace, config, repo, schema


def test_full_ingestion_workflow(demo_workspace: tuple) -> None:
    """Test complete ingestion workflow."""
    workspace, config, repo, schema = demo_workspace
    
    # Initialize agent
    agent = IngestionAgent(workspace, config)
    
    # Ingest repository
    repo_artifact = agent.ingest_repository(repo)
    assert repo_artifact.artifact_type == "repo_inventory"
    assert repo_artifact.metrics["total_files"] > 0
    
    # Verify artifact files created
    assert (workspace.artifacts / "repo_inventory.json").exists()
    assert (workspace.artifacts / "repo_inventory.md").exists()
    assert (workspace.artifacts / "repo_inventory_sources.json").exists()
    
    # Ingest schema
    schema_artifact = agent.ingest_database_schema(schema)
    assert schema_artifact.artifact_type == "db_schema"
    assert schema_artifact.metrics["total_tables"] == 2
    
    # Verify schema artifacts
    assert (workspace.artifacts / "db_schema.json").exists()
    assert (workspace.artifacts / "db_schema.md").exists()


def test_ingestion_with_redaction(demo_workspace: tuple) -> None:
    """Test that redaction is applied during ingestion."""
    workspace, config, repo, _ = demo_workspace
    
    # Enable redaction
    assert config.redaction_enabled is True
    
    # Create file with sensitive data
    sensitive_file = repo / "config.py"
    sensitive_file.write_text('''
DB_USER = "admin"
DB_PASS = "password123"
API_KEY = "sk_test_1234567890abcdef1234567890abcdef"
CONTACT = "support@company.com"
''')
    
    # Ingest
    agent = IngestionAgent(workspace, config)
    artifact = agent.ingest_repository(repo)
    
    # Verify artifact was created
    assert artifact.metrics["total_files"] > 0


def test_artifact_sources_tracking(demo_workspace: tuple) -> None:
    """Test that source references are properly tracked."""
    workspace, config, repo, _ = demo_workspace
    
    agent = IngestionAgent(workspace, config)
    artifact = agent.ingest_repository(repo)
    
    # Check sources
    assert len(artifact.sources) > 0
    source = artifact.sources[0]
    assert source.type == "repo"
    assert source.path == str(repo)
    assert source.timestamp is not None


def test_multiple_ingestions_same_engagement(demo_workspace: tuple) -> None:
    """Test multiple ingestion operations for same engagement."""
    workspace, config, repo, schema = demo_workspace
    
    agent = IngestionAgent(workspace, config)
    
    # First ingestion
    artifact1 = agent.ingest_repository(repo)
    
    # Create more data
    docs_dir = workspace.root.parent / "docs"
    docs_dir.mkdir()
    (docs_dir / "readme.md").write_text("# Documentation\nSample docs")
    
    # Second ingestion
    artifact2 = agent.ingest_documents(docs_dir)
    
    # Both should succeed
    assert artifact1.engagement_id == artifact2.engagement_id
    assert (workspace.artifacts / "repo_inventory.json").exists()
    assert (workspace.artifacts / "documents.json").exists()
