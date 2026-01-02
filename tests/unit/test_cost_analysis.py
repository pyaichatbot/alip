"""Unit tests for CostAnalysisAgent."""

import pytest
from pathlib import Path
from datetime import datetime

from agents.cost_analysis import CostAnalysisAgent
from core.models import AnalysisArtifact, SourceReference, EngagementConfig
from skills.workspace import init_workspace, load_engagement_config


@pytest.fixture
def sample_workspace(tmp_path: Path):
    """Create sample workspace."""
    engagement_id = "test-cost-001"
    workspace = init_workspace(
        engagement_id=engagement_id,
        client_name="Test Corp",
        base_dir=tmp_path,
        config_overrides={"read_only_mode": True, "state": "analyzed"}
    )
    
    config = load_engagement_config(workspace)
    
    return workspace, config


@pytest.fixture
def sample_query_logs_artifact():
    """Create sample query logs artifact."""
    events = [
        # Slow SELECT query - executed many times
        {'query': 'SELECT * FROM users WHERE email = "test@example.com"', 'duration_ms': 150.0},
        {'query': 'SELECT * FROM users WHERE email = "admin@example.com"', 'duration_ms': 160.0},
        {'query': 'SELECT * FROM users WHERE email = "user@example.com"', 'duration_ms': 145.0},
        
        # Fast query but very frequent
        {'query': 'SELECT id FROM sessions WHERE user_id = 123', 'duration_ms': 5.0},
        {'query': 'SELECT id FROM sessions WHERE user_id = 456', 'duration_ms': 6.0},
        {'query': 'SELECT id FROM sessions WHERE user_id = 789', 'duration_ms': 5.5},
        {'query': 'SELECT id FROM sessions WHERE user_id = 101', 'duration_ms': 5.2},
        {'query': 'SELECT id FROM sessions WHERE user_id = 202', 'duration_ms': 5.8},
        
        # Expensive INSERT
        {'query': 'INSERT INTO audit_log (user_id, action) VALUES (1, "login")', 'duration_ms': 80.0},
        {'query': 'INSERT INTO audit_log (user_id, action) VALUES (2, "logout")', 'duration_ms': 85.0},
    ]
    
    return AnalysisArtifact(
        artifact_type='query_logs',
        engagement_id='test-cost-001',
        data={'events': events},
        sources=[],
        metrics={}
    )


@pytest.fixture
def sample_db_schema_artifact():
    """Create sample database schema artifact."""
    schema = {
        'tables': [
            {
                'name': 'users',
                'columns': [
                    {'name': 'id', 'type': 'INTEGER'},
                    {'name': 'email', 'type': 'TEXT'},
                    {'name': 'name', 'type': 'TEXT'},
                ],
                'indexes': [
                    {'name': 'idx_users_id', 'columns': ['id']}
                    # Note: missing index on email
                ]
            },
            {
                'name': 'sessions',
                'columns': [
                    {'name': 'id', 'type': 'INTEGER'},
                    {'name': 'user_id', 'type': 'INTEGER'},
                ],
                'indexes': [
                    {'name': 'idx_sessions_user', 'columns': ['user_id']}
                ]
            },
            {
                'name': 'audit_log',
                'columns': [
                    {'name': 'id', 'type': 'INTEGER'},
                    {'name': 'user_id', 'type': 'INTEGER'},
                    {'name': 'action', 'type': 'TEXT'},
                ],
                'indexes': []
            }
        ]
    }
    
    return AnalysisArtifact(
        artifact_type='database',
        engagement_id='test-cost-001',
        data=schema,
        sources=[],
        metrics={}
    )


@pytest.fixture
def sample_topology_artifact():
    """Create sample topology artifact."""
    topology = {
        'nodes': [
            {'id': 'module:user_service.py', 'type': 'module'},
            {'id': 'module:session_service.py', 'type': 'module'},
            {'id': 'table:users', 'type': 'table'},
            {'id': 'table:sessions', 'type': 'table'},
        ],
        'edges': [
            {'source': 'module:user_service.py', 'target': 'table:users', 'type': 'uses'},
            {'source': 'module:session_service.py', 'target': 'table:sessions', 'type': 'uses'},
        ]
    }
    
    return AnalysisArtifact(
        artifact_type='topology',
        engagement_id='test-cost-001',
        data=topology,
        sources=[],
        metrics={}
    )


def test_cost_agent_initialization(sample_workspace):
    """Test CostAnalysisAgent can be initialized."""
    workspace, config = sample_workspace
    
    agent = CostAnalysisAgent(workspace, config)
    
    assert agent.workspace == workspace
    assert agent.config == config


def test_normalize_query(sample_workspace):
    """Test query normalization."""
    workspace, config = sample_workspace
    agent = CostAnalysisAgent(workspace, config)
    
    # Test string literal removal
    query1 = "SELECT * FROM users WHERE email = 'test@example.com'"
    normalized1 = agent._normalize_query(query1)
    assert "'test@example.com'" not in normalized1
    assert "'?'" in normalized1
    
    # Test numeric literal removal
    query2 = "SELECT * FROM users WHERE id = 123"
    normalized2 = agent._normalize_query(query2)
    assert "123" not in normalized2
    assert "?" in normalized2
    
    # Test that similar queries normalize to same pattern
    query3a = "SELECT * FROM users WHERE id = 456"
    query3b = "SELECT * FROM users WHERE id = 789"
    assert agent._normalize_query(query3a) == agent._normalize_query(query3b)


def test_aggregate_query_stats(sample_workspace, sample_query_logs_artifact):
    """Test query aggregation."""
    workspace, config = sample_workspace
    agent = CostAnalysisAgent(workspace, config)
    
    events = sample_query_logs_artifact.data['events']
    stats = agent._aggregate_query_stats(events)
    
    # Should group similar queries
    assert len(stats) < len(events)  # Some queries should be grouped
    
    # Check that stats are calculated
    for pattern, stat in stats.items():
        assert stat['count'] > 0
        assert stat['avg_duration_ms'] > 0
        assert stat['min_duration_ms'] <= stat['avg_duration_ms']
        assert stat['max_duration_ms'] >= stat['avg_duration_ms']


def test_calculate_costs(sample_workspace, sample_query_logs_artifact):
    """Test cost calculation."""
    workspace, config = sample_workspace
    agent = CostAnalysisAgent(workspace, config)
    
    events = sample_query_logs_artifact.data['events']
    stats = agent._aggregate_query_stats(events)
    cost_drivers = agent._calculate_costs(stats)
    
    # Should return cost drivers
    assert len(cost_drivers) > 0
    
    # Check structure
    for driver in cost_drivers:
        assert 'query_pattern' in driver
        assert 'execution_count' in driver
        assert 'avg_duration_ms' in driver
        assert 'total_cost_ms' in driver
        assert 'impact' in driver
        
        # Cost should be duration × count
        expected_cost = driver['avg_duration_ms'] * driver['execution_count']
        assert abs(driver['total_cost_ms'] - expected_cost) < 0.1
        
        # Impact should be classified correctly
        if driver['total_cost_ms'] > 10000:
            assert driver['impact'] == 'HIGH'
        elif driver['total_cost_ms'] > 1000:
            assert driver['impact'] == 'MEDIUM'
        else:
            assert driver['impact'] == 'LOW'


def test_extract_table_name(sample_workspace):
    """Test table name extraction."""
    workspace, config = sample_workspace
    agent = CostAnalysisAgent(workspace, config)
    
    # FROM clause
    query1 = "SELECT * FROM users WHERE id = 1"
    assert agent._extract_table_name(query1) == 'users'
    
    # INTO clause
    query2 = "INSERT INTO orders (user_id) VALUES (123)"
    assert agent._extract_table_name(query2) == 'orders'
    
    # UPDATE clause
    query3 = "UPDATE products SET price = 100 WHERE id = 5"
    assert agent._extract_table_name(query3) == 'products'


def test_detect_missing_indexes(
    sample_workspace,
    sample_query_logs_artifact,
    sample_db_schema_artifact
):
    """Test missing index detection."""
    workspace, config = sample_workspace
    agent = CostAnalysisAgent(workspace, config)
    
    events = sample_query_logs_artifact.data['events']
    stats = agent._aggregate_query_stats(events)
    cost_drivers = agent._calculate_costs(stats)
    
    # Detect missing indexes
    schema = sample_db_schema_artifact.data
    cost_drivers = agent._detect_missing_indexes(cost_drivers, schema)
    
    # Should detect missing index on users.email
    users_drivers = [d for d in cost_drivers if d.get('table') == 'users']
    if users_drivers:
        # email is used in WHERE but not indexed
        assert any('email' in d.get('missing_indexes', []) for d in users_drivers)


def test_extract_where_columns(sample_workspace):
    """Test WHERE clause column extraction."""
    workspace, config = sample_workspace
    agent = CostAnalysisAgent(workspace, config)
    
    # Single column
    query1 = "SELECT * FROM users WHERE email = 'test@example.com'"
    columns1 = agent._extract_where_columns(query1)
    assert 'email' in columns1
    
    # Multiple columns
    query2 = "SELECT * FROM orders WHERE user_id = 123 AND status = 'active'"
    columns2 = agent._extract_where_columns(query2)
    assert 'user_id' in columns2
    assert 'status' in columns2
    
    # IN clause
    query3 = "SELECT * FROM products WHERE category IN ('books', 'electronics')"
    columns3 = agent._extract_where_columns(query3)
    assert 'category' in columns3


def test_enrich_with_topology(
    sample_workspace,
    sample_query_logs_artifact,
    sample_db_schema_artifact,
    sample_topology_artifact
):
    """Test topology enrichment."""
    workspace, config = sample_workspace
    agent = CostAnalysisAgent(workspace, config)
    
    events = sample_query_logs_artifact.data['events']
    stats = agent._aggregate_query_stats(events)
    cost_drivers = agent._calculate_costs(stats)
    
    # Enrich with topology
    cost_drivers = agent._enrich_with_topology(cost_drivers, sample_topology_artifact)
    
    # Should add affected components
    users_drivers = [d for d in cost_drivers if d.get('table') == 'users']
    if users_drivers:
        driver = users_drivers[0]
        assert 'affected_components' in driver
        # user_service.py uses users table
        assert any('user_service' in comp for comp in driver.get('affected_components', []))


def test_analyze_costs_minimal(
    sample_workspace,
    sample_db_schema_artifact,
    sample_topology_artifact
):
    """Test cost analysis with no query logs."""
    workspace, config = sample_workspace
    agent = CostAnalysisAgent(workspace, config)
    
    # No query logs
    result = agent.analyze_costs(None, sample_db_schema_artifact, sample_topology_artifact)
    
    # Should return minimal artifact
    assert result.artifact_type == 'cost_drivers'
    assert result.data['summary']['total_queries_analyzed'] == 0
    assert len(result.data['cost_drivers']) == 0


def test_analyze_costs_complete(
    sample_workspace,
    sample_query_logs_artifact,
    sample_db_schema_artifact,
    sample_topology_artifact
):
    """Test complete cost analysis."""
    workspace, config = sample_workspace
    agent = CostAnalysisAgent(workspace, config)
    
    result = agent.analyze_costs(
        sample_query_logs_artifact,
        sample_db_schema_artifact,
        sample_topology_artifact
    )
    
    # Should return analysis artifact
    assert result.artifact_type == 'cost_drivers'
    assert result.engagement_id == config.engagement_id
    
    # Should have cost drivers
    assert len(result.data['cost_drivers']) > 0
    
    # Should have summary
    summary = result.data['summary']
    assert summary['total_queries_analyzed'] > 0
    assert summary['unique_query_patterns'] > 0
    
    # Should save artifacts
    assert (workspace.artifacts / 'cost_drivers.json').exists()
    assert (workspace.artifacts / 'cost_drivers.md').exists()


def test_cost_ranking(
    sample_workspace,
    sample_query_logs_artifact,
    sample_db_schema_artifact,
    sample_topology_artifact
):
    """Test that cost drivers are ranked by total cost."""
    workspace, config = sample_workspace
    agent = CostAnalysisAgent(workspace, config)
    
    result = agent.analyze_costs(
        sample_query_logs_artifact,
        sample_db_schema_artifact,
        sample_topology_artifact
    )
    
    cost_drivers = result.data['cost_drivers']
    
    # Should be sorted by total_cost_ms (descending)
    costs = [d['total_cost_ms'] for d in cost_drivers]
    assert costs == sorted(costs, reverse=True)
    
    # Should limit to top 10
    assert len(cost_drivers) <= 10


def test_markdown_generation(
    sample_workspace,
    sample_query_logs_artifact,
    sample_db_schema_artifact,
    sample_topology_artifact
):
    """Test markdown report generation."""
    workspace, config = sample_workspace
    agent = CostAnalysisAgent(workspace, config)
    
    result = agent.analyze_costs(
        sample_query_logs_artifact,
        sample_db_schema_artifact,
        sample_topology_artifact
    )
    
    # Check markdown file
    md_path = workspace.artifacts / 'cost_drivers.md'
    assert md_path.exists()
    
    content = md_path.read_text()
    
    # Should have header
    assert '# Cost Analysis Report' in content
    
    # Should have summary
    assert 'Summary' in content
    
    # Should have cost drivers
    assert 'Top Cost Drivers' in content or 'No cost drivers' in content
