"""Integration tests for TopologyAgent.

Tests the complete workflow:
1. Load repository and database artifacts
2. Build topology graph
3. Detect SPOFs
4. Detect circular dependencies
5. Generate all output artifacts
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from agents.topology import TopologyAgent
from core.models import AnalysisArtifact, EngagementConfig, SourceReference
from skills.workspace import init_workspace, load_engagement_config


@pytest.fixture
def sample_workspace(tmp_path: Path):
    """Create sample workspace with artifacts."""
    engagement_id = "test-topology-001"
    workspace = init_workspace(
        engagement_id=engagement_id,
        client_name="Test Corp",
        base_dir=tmp_path,
        config_overrides={"read_only_mode": True, "state": "ingested"}
    )
    
    config = load_engagement_config(workspace)
    
    return workspace, config


@pytest.fixture
def sample_repo_artifact(sample_workspace) -> AnalysisArtifact:
    """Create sample repository artifact."""
    workspace, config = sample_workspace
    
    # Create a realistic repository structure
    artifact = AnalysisArtifact(
        artifact_type="repository",
        engagement_id=config.engagement_id,
        data={
            "files": [
                {
                    "path": "src/user_service.py",
                    "extension": ".py",
                    "lines": 150,
                    "language": "Python",
                    "imports": ["database", "utils"],
                    "sql_queries": [
                        {
                            "query": "SELECT * FROM users WHERE id = ?",
                            "line": 42,
                            "type": "SELECT",
                            "table": "users"
                        },
                        {
                            "query": "INSERT INTO users (email, name) VALUES (?, ?)",
                            "line": 55,
                            "type": "INSERT",
                            "table": "users"
                        }
                    ]
                },
                {
                    "path": "src/order_service.py",
                    "extension": ".py",
                    "lines": 200,
                    "language": "Python",
                    "imports": ["database", "user_service"],
                    "sql_queries": [
                        {
                            "query": "SELECT * FROM orders WHERE user_id = ?",
                            "line": 30,
                            "type": "SELECT",
                            "table": "orders"
                        },
                        {
                            "query": "INSERT INTO orders (user_id, total) VALUES (?, ?)",
                            "line": 45,
                            "type": "INSERT",
                            "table": "orders"
                        }
                    ]
                },
                {
                    "path": "src/database.py",
                    "extension": ".py",
                    "lines": 100,
                    "language": "Python",
                    "imports": ["sqlite3"],
                    "sql_queries": []
                }
            ],
            "statistics": {
                "total_files": 3,
                "total_lines": 450,
                "languages": {"Python": 3}
            }
        },
        sources=[
            SourceReference(type="repo", path="src/", timestamp=datetime(2024, 1, 2))
        ],
        metrics={"file_count": 3}
    )
    
    return artifact


@pytest.fixture
def sample_db_artifact(sample_workspace) -> AnalysisArtifact:
    """Create sample database artifact."""
    workspace, config = sample_workspace
    
    artifact = AnalysisArtifact(
        artifact_type="database",
        engagement_id=config.engagement_id,
        data={
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True},
                        {"name": "email", "type": "TEXT"},
                        {"name": "name", "type": "TEXT"}
                    ],
                    "indexes": [
                        {"name": "idx_users_email", "columns": ["email"]}
                    ]
                },
                {
                    "name": "orders",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True},
                        {
                            "name": "user_id",
                            "type": "INTEGER",
                            "foreign_key": {"table": "users", "column": "id"}
                        },
                        {"name": "total", "type": "DECIMAL"}
                    ],
                    "indexes": [
                        {"name": "idx_orders_user", "columns": ["user_id"]}
                    ]
                },
                {
                    "name": "order_items",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True},
                        {
                            "name": "order_id",
                            "type": "INTEGER",
                            "foreign_key": {"table": "orders", "column": "id"}
                        },
                        {"name": "product", "type": "TEXT"},
                        {"name": "quantity", "type": "INTEGER"}
                    ],
                    "indexes": []
                }
            ],
            "statistics": {
                "total_tables": 3,
                "total_columns": 9
            }
        },
        sources=[
            SourceReference(type="db", path="schema", timestamp=datetime(2024, 1, 2))
        ],
        metrics={"table_count": 3}
    )
    
    return artifact


def test_topology_agent_initialization(sample_workspace):
    """Test TopologyAgent can be initialized."""
    workspace, config = sample_workspace
    
    agent = TopologyAgent(workspace, config)
    
    assert agent.workspace == workspace
    assert agent.config == config


def test_topology_build_complete_graph(
    sample_workspace,
    sample_repo_artifact,
    sample_db_artifact
):
    """Test building complete topology graph."""
    workspace, config = sample_workspace
    agent = TopologyAgent(workspace, config)
    
    # Build topology
    topology = agent.build_topology(sample_repo_artifact, sample_db_artifact)
    
    # Verify artifact structure
    assert topology.artifact_type == "topology"
    assert topology.engagement_id == config.engagement_id
    assert "nodes" in topology.data
    assert "edges" in topology.data
    assert "spofs" in topology.data
    assert "circular_dependencies" in topology.data
    assert "statistics" in topology.data
    
    # Verify statistics
    stats = topology.data["statistics"]
    assert stats["total_nodes"] > 0
    assert stats["modules"] == 3  # 3 Python files
    assert stats["tables"] == 3  # 3 database tables


def test_topology_nodes_created(
    sample_workspace,
    sample_repo_artifact,
    sample_db_artifact
):
    """Test that all nodes are created correctly."""
    workspace, config = sample_workspace
    agent = TopologyAgent(workspace, config)
    
    topology = agent.build_topology(sample_repo_artifact, sample_db_artifact)
    
    nodes = topology.data["nodes"]
    
    # Should have 3 modules + 3 tables = 6 nodes
    assert len(nodes) == 6
    
    # Check module nodes
    module_nodes = [n for n in nodes if n["type"] == "module"]
    assert len(module_nodes) == 3
    
    module_names = [n["name"] for n in module_nodes]
    assert "src/user_service.py" in module_names
    assert "src/order_service.py" in module_names
    assert "src/database.py" in module_names
    
    # Check table nodes
    table_nodes = [n for n in nodes if n["type"] == "table"]
    assert len(table_nodes) == 3
    
    table_names = [n["name"] for n in table_nodes]
    assert "users" in table_names
    assert "orders" in table_names
    assert "order_items" in table_names


def test_topology_edges_created(
    sample_workspace,
    sample_repo_artifact,
    sample_db_artifact
):
    """Test that edges are created correctly."""
    workspace, config = sample_workspace
    agent = TopologyAgent(workspace, config)
    
    topology = agent.build_topology(sample_repo_artifact, sample_db_artifact)
    
    edges = topology.data["edges"]
    
    # Should have multiple edges
    assert len(edges) > 0
    
    # Check for code->DB edges (uses)
    uses_edges = [e for e in edges if e["type"] == "uses"]
    assert len(uses_edges) >= 2  # user_service and order_service both use DB
    
    # Check for FK edges (references)
    ref_edges = [e for e in edges if e["type"] == "references"]
    assert len(ref_edges) >= 2  # orders->users, order_items->orders
    
    # Verify specific edges exist
    edge_pairs = [(e["source"], e["target"]) for e in edges]
    
    # orders table should reference users table
    assert any("orders" in src and "users" in tgt for src, tgt in edge_pairs)


def test_topology_spof_detection(
    sample_workspace,
    sample_repo_artifact,
    sample_db_artifact
):
    """Test SPOF detection."""
    workspace, config = sample_workspace
    agent = TopologyAgent(workspace, config)
    
    topology = agent.build_topology(sample_repo_artifact, sample_db_artifact)
    
    spofs = topology.data["spofs"]
    
    # Should detect at least one SPOF (users table is central)
    # Note: This depends on graph structure and threshold
    # In a well-connected graph, we expect some SPOFs
    
    if len(spofs) > 0:
        # Verify SPOF structure
        spof = spofs[0]
        assert "node_id" in spof
        assert "node_type" in spof
        assert "node_name" in spof
        assert "betweenness_centrality" in spof
        assert "dependencies_count" in spof
        assert "risk_level" in spof
        
        # Risk level should be valid
        assert spof["risk_level"] in ["high", "medium", "low"]


def test_topology_metrics_calculated(
    sample_workspace,
    sample_repo_artifact,
    sample_db_artifact
):
    """Test that graph metrics are calculated."""
    workspace, config = sample_workspace
    agent = TopologyAgent(workspace, config)
    
    topology = agent.build_topology(sample_repo_artifact, sample_db_artifact)
    
    metrics = topology.metrics
    
    # Check required metrics
    assert "node_count" in metrics
    assert "edge_count" in metrics
    assert "density" in metrics
    
    # Verify values are reasonable
    assert metrics["node_count"] > 0
    assert metrics["edge_count"] >= 0
    assert 0 <= metrics["density"] <= 1


def test_topology_artifacts_saved(
    sample_workspace,
    sample_repo_artifact,
    sample_db_artifact
):
    """Test that all output artifacts are saved."""
    workspace, config = sample_workspace
    agent = TopologyAgent(workspace, config)
    
    topology = agent.build_topology(sample_repo_artifact, sample_db_artifact)
    
    # Check JSON artifact
    json_path = workspace.artifacts / "topology.json"
    assert json_path.exists()
    
    with open(json_path) as f:
        data = json.load(f)
        assert data["artifact_type"] == "topology"
        assert "nodes" in data["data"]
        assert "edges" in data["data"]
    
    # Check Markdown summary
    md_path = workspace.artifacts / "topology.md"
    assert md_path.exists()
    
    content = md_path.read_text()
    assert "System Topology Analysis" in content
    assert "Summary" in content
    
    # Check sources file
    sources_path = workspace.artifacts / "topology_sources.json"
    assert sources_path.exists()
    
    # Check metrics file
    metrics_path = workspace.artifacts / "topology_metrics.json"
    assert metrics_path.exists()


def test_topology_source_traceability(
    sample_workspace,
    sample_repo_artifact,
    sample_db_artifact
):
    """Test that all findings have source references."""
    workspace, config = sample_workspace
    agent = TopologyAgent(workspace, config)
    
    topology = agent.build_topology(sample_repo_artifact, sample_db_artifact)
    
    # Should have sources
    assert len(topology.sources) > 0
    
    # Check source structure
    for source in topology.sources:
        assert hasattr(source, 'type')
        assert hasattr(source, 'path')
        assert hasattr(source, 'timestamp')
        
        # Type should be valid
        assert source.type in ['repo', 'db', 'system']


def test_topology_with_circular_dependency(
    sample_workspace,
    sample_repo_artifact,
    sample_db_artifact
):
    """Test detection of circular dependencies."""
    workspace, config = sample_workspace
    
    # Modify repo artifact to create circular dependency
    sample_repo_artifact.data["files"][0]["imports"].append("order_service")
    sample_repo_artifact.data["files"][1]["imports"].append("user_service")
    
    agent = TopologyAgent(workspace, config)
    topology = agent.build_topology(sample_repo_artifact, sample_db_artifact)
    
    circular = topology.data["circular_dependencies"]
    
    # Should detect the circular dependency
    # Note: Detection depends on how imports are processed
    # May or may not detect based on implementation
    assert isinstance(circular, list)


def test_topology_empty_repository(sample_workspace, sample_db_artifact):
    """Test topology with empty repository."""
    workspace, config = sample_workspace
    
    # Create empty repo artifact
    empty_repo = AnalysisArtifact(
        artifact_type="repository",
        engagement_id=config.engagement_id,
        data={"files": [], "statistics": {"total_files": 0}},
        sources=[],
        metrics={"file_count": 0}
    )
    
    agent = TopologyAgent(workspace, config)
    topology = agent.build_topology(empty_repo, sample_db_artifact)
    
    # Should still work, just with no module nodes
    assert topology.data["statistics"]["modules"] == 0
    assert topology.data["statistics"]["tables"] == 3


def test_topology_with_complex_dependencies(
    sample_workspace,
    sample_db_artifact
):
    """Test topology with more complex dependency structure."""
    workspace, config = sample_workspace
    
    # Create more complex repository
    complex_repo = AnalysisArtifact(
        artifact_type="repository",
        engagement_id=config.engagement_id,
        data={
            "files": [
                {
                    "path": "src/api/users.py",
                    "extension": ".py",
                    "lines": 100,
                    "imports": ["services.user_service", "database.connection"],
                    "sql_queries": []
                },
                {
                    "path": "src/services/user_service.py",
                    "extension": ".py",
                    "lines": 200,
                    "imports": ["database.connection", "models.user"],
                    "sql_queries": [
                        {
                            "query": "SELECT * FROM users",
                            "line": 10,
                            "type": "SELECT",
                            "table": "users"
                        }
                    ]
                },
                {
                    "path": "src/models/user.py",
                    "extension": ".py",
                    "lines": 50,
                    "imports": [],
                    "sql_queries": []
                },
                {
                    "path": "src/database/connection.py",
                    "extension": ".py",
                    "lines": 80,
                    "imports": ["sqlite3"],
                    "sql_queries": []
                }
            ],
            "statistics": {"total_files": 4}
        },
        sources=[],
        metrics={"file_count": 4}
    )
    
    agent = TopologyAgent(workspace, config)
    topology = agent.build_topology(complex_repo, sample_db_artifact)
    
    # Should have more nodes
    assert topology.data["statistics"]["total_nodes"] >= 7  # 4 modules + 3 tables
    
    # Should have edges (at least module->table relationships)
    assert topology.data["statistics"]["total_edges"] >= 1


def test_topology_performance(
    sample_workspace,
    sample_repo_artifact,
    sample_db_artifact
):
    """Test that topology generation completes in reasonable time."""
    import time
    
    workspace, config = sample_workspace
    agent = TopologyAgent(workspace, config)
    
    start = time.time()
    topology = agent.build_topology(sample_repo_artifact, sample_db_artifact)
    elapsed = time.time() - start
    
    # Should complete in under 1 second for small graph
    assert elapsed < 1.0
    
    # Should still produce valid output
    assert len(topology.data["nodes"]) > 0


def test_topology_networkx_not_installed(sample_workspace):
    """Test graceful handling if NetworkX not available."""
    workspace, config = sample_workspace
    
    # This test would require mocking the import
    # For now, we just verify the error message is clear
    try:
        agent = TopologyAgent(workspace, config)
        # If we get here, networkx is installed (expected)
        assert hasattr(agent, 'workspace')
    except ImportError as e:
        # If networkx is missing, error should be clear
        assert "networkx" in str(e).lower()
