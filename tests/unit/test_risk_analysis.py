"""Unit tests for RiskAnalysisAgent."""

import pytest
from pathlib import Path
from datetime import datetime

from agents.risk_analysis import RiskAnalysisAgent
from core.models import AnalysisArtifact, SourceReference, EngagementConfig
from skills.workspace import init_workspace, load_engagement_config


@pytest.fixture
def sample_workspace(tmp_path: Path):
    """Create sample workspace."""
    engagement_id = "test-risk-001"
    workspace = init_workspace(
        engagement_id=engagement_id,
        client_name="Test Corp",
        base_dir=tmp_path,
        config_overrides={"read_only_mode": True, "state": "analyzed"}
    )
    
    config = load_engagement_config(workspace)
    
    return workspace, config


@pytest.fixture
def sample_topology_artifact():
    """Create sample topology with SPOFs."""
    topology = {
        'nodes': [
            {'id': 'module:database.py', 'type': 'module'},
            {'id': 'table:users', 'type': 'table'},
            {'id': 'table:orders', 'type': 'table'},
        ],
        'edges': [
            {'source': 'module:database.py', 'target': 'table:users', 'type': 'uses'},
            {'source': 'module:database.py', 'target': 'table:orders', 'type': 'uses'},
        ],
        'spofs': [
            {
                'node_name': 'database.py',
                'node_type': 'module',
                'risk_level': 'high',
                'centrality': 0.85,
                'dependent_components': ['user_service.py', 'order_service.py']
            },
            {
                'node_name': 'users',
                'node_type': 'table',
                'risk_level': 'critical',
                'centrality': 0.92,
                'dependent_components': ['database.py', 'auth_service.py']
            }
        ]
    }
    
    return AnalysisArtifact(
        artifact_type='topology',
        engagement_id='test-risk-001',
        data=topology,
        sources=[],
        metrics={}
    )


@pytest.fixture
def sample_docs_artifact():
    """Create sample documentation with issues."""
    docs = {
        'documents': [
            {
                'path': 'runbook.md',
                'text_content': '''
# Deployment Runbook

To deploy:
1. Manually SSH into production server
2. Run the deployment script
3. Contact John if there are issues
4. Ask Sarah about database migrations
5. Only Mark knows the production password
6. Contact John for production access
                '''
            },
            {
                'path': 'README.md',
                'text_content': '''
# System README

For questions, reach out to Alice.
If the system crashes, contact Bob immediately.
Ask Sarah about the database schema.
                '''
            }
        ]
    }
    
    return AnalysisArtifact(
        artifact_type='documents',
        engagement_id='test-risk-001',
        data=docs,
        sources=[],
        metrics={}
    )


@pytest.fixture
def sample_repo_artifact():
    """Create sample repository with security issues."""
    files = [
        {
            'path': 'src/config.py',
            'content': '''
# Configuration
DB_HOST = "localhost"
DB_USER = "admin"
DB_PASSWORD = "secret123"  # Hardcoded password!
API_KEY = "sk-1234567890abcdef"
            '''
        },
        {
            'path': 'src/database.py',
            'content': '''
import sqlite3

def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection
    return execute(query)
            '''
        },
        {
            'path': 'src/api.py',
            'content': '''
import requests

def fetch_data():
    # Insecure connection
    response = requests.get("http://api.example.com", verify=False)
    return response.json()
            '''
        }
    ]
    
    return AnalysisArtifact(
        artifact_type='repository',
        engagement_id='test-risk-001',
        data={'files': files},
        sources=[],
        metrics={}
    )


@pytest.fixture
def sample_db_artifact():
    """Create sample database schema."""
    schema = {
        'tables': [
            {
                'name': 'users',
                'columns': [
                    {'name': 'id', 'type': 'INTEGER'},
                    {'name': 'email', 'type': 'TEXT'},
                ],
                'indexes': [
                    {'name': 'idx_users_id', 'columns': ['id']}
                ]
            },
            {
                'name': 'sessions',
                'columns': [
                    {'name': 'id', 'type': 'INTEGER'},
                    {'name': 'user_id', 'type': 'INTEGER'},
                ],
                'indexes': []  # No indexes!
            }
        ]
    }
    
    return AnalysisArtifact(
        artifact_type='database',
        engagement_id='test-risk-001',
        data=schema,
        sources=[],
        metrics={}
    )


def test_risk_agent_initialization(sample_workspace):
    """Test RiskAnalysisAgent can be initialized."""
    workspace, config = sample_workspace
    
    agent = RiskAnalysisAgent(workspace, config)
    
    assert agent.workspace == workspace
    assert agent.config == config


def test_detect_spofs(sample_workspace, sample_topology_artifact):
    """Test SPOF detection."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    spof_risks = agent._detect_spofs(sample_topology_artifact)
    
    # Should detect 2 SPOFs
    assert len(spof_risks) == 2
    
    # Check structure
    for risk in spof_risks:
        assert 'title' in risk
        assert 'SPOF:' in risk['title']
        assert 'severity' in risk
        assert risk['category'] == 'spof'
        assert 'evidence' in risk
        assert len(risk['evidence']) > 0
    
    # Check severity mapping
    severities = [r['severity'] for r in spof_risks]
    assert 'CRITICAL' in severities or 'HIGH' in severities


def test_detect_tribal_knowledge(sample_workspace, sample_docs_artifact):
    """Test tribal knowledge detection."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    tribal_risks = agent._detect_tribal_knowledge(sample_docs_artifact)
    
    # Should detect mentions of John, Sarah, Mark, Alice, Bob
    assert len(tribal_risks) > 0
    
    # Check structure
    for risk in tribal_risks:
        assert 'title' in risk
        assert 'Tribal Knowledge:' in risk['title']
        assert risk['category'] == 'tribal_knowledge'
        assert 'person_name' in risk
        assert 'mention_count' in risk
        assert risk['mention_count'] >= 1


def test_detect_manual_operations(sample_workspace, sample_docs_artifact):
    """Test manual operation detection."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    manual_risks = agent._detect_manual_operations(sample_docs_artifact)
    
    # Should detect manual SSH, manual run
    assert len(manual_risks) > 0
    
    # Check structure
    for risk in manual_risks:
        assert 'title' in risk
        assert 'Manual Operations' in risk['title']
        assert risk['category'] == 'manual_ops'
        assert 'operation_count' in risk


def test_detect_security_issues(sample_workspace, sample_repo_artifact):
    """Test security vulnerability detection."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    security_risks = agent._detect_security_issues(sample_repo_artifact)
    
    # Should detect hardcoded password, API key, SQL injection, insecure connection
    assert len(security_risks) >= 3  # At least 3 issues
    
    # Check structure
    for risk in security_risks:
        assert 'title' in risk
        assert 'Security:' in risk['title']
        assert risk['category'] == 'security'
        assert 'issue_type' in risk
        assert risk['severity'] in ['CRITICAL', 'HIGH', 'MEDIUM']
    
    # Check specific issues found
    issue_types = [r['issue_type'] for r in security_risks]
    assert 'hardcoded_password' in issue_types or 'api_key' in issue_types


def test_detect_documentation_gaps(
    sample_workspace,
    sample_repo_artifact,
    sample_docs_artifact
):
    """Test documentation gap detection."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    doc_risks = agent._detect_documentation_gaps(
        sample_repo_artifact,
        sample_docs_artifact
    )
    
    # May or may not detect gaps depending on ratio
    # Just verify structure if any found
    for risk in doc_risks:
        assert 'title' in risk
        assert risk['category'] == 'documentation'
        assert 'code_file_count' in risk
        assert 'doc_file_count' in risk


def test_detect_database_risks(
    sample_workspace,
    sample_db_artifact,
    sample_topology_artifact
):
    """Test database risk detection."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    db_risks = agent._detect_database_risks(
        sample_db_artifact,
        sample_topology_artifact
    )
    
    # Should detect sessions table without indexes
    assert len(db_risks) > 0
    
    risk = db_risks[0]
    assert 'Tables Without Indexes' in risk['title']
    assert 'sessions' in risk['table_names']


def test_calculate_risk_scores(sample_workspace):
    """Test risk score calculation."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    risks = [
        {'severity': 'CRITICAL', 'confidence': 'high'},
        {'severity': 'HIGH', 'confidence': 'medium'},
        {'severity': 'MEDIUM', 'confidence': 'low'},
        {'severity': 'LOW', 'confidence': 'high'},
    ]
    
    risks = agent._calculate_risk_scores(risks)
    
    # Should have risk_score field
    for risk in risks:
        assert 'risk_score' in risk
        assert risk['risk_score'] > 0
    
    # CRITICAL/high should have highest score
    assert risks[0]['risk_score'] > risks[1]['risk_score']
    assert risks[1]['risk_score'] > risks[2]['risk_score']


def test_rank_risks(sample_workspace):
    """Test risk ranking."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    risks = [
        {'severity': 'MEDIUM', 'confidence': 'high', 'risk_score': 4.0},
        {'severity': 'CRITICAL', 'confidence': 'high', 'risk_score': 10.0},
        {'severity': 'HIGH', 'confidence': 'medium', 'risk_score': 7.0},
        {'severity': 'LOW', 'confidence': 'low', 'risk_score': 0.8},
    ]
    
    ranked = agent._rank_risks(risks)
    
    # Should be sorted by risk_score (descending)
    scores = [r['risk_score'] for r in ranked]
    assert scores == sorted(scores, reverse=True)
    
    # CRITICAL should be first
    assert ranked[0]['severity'] == 'CRITICAL'


def test_extract_context(sample_workspace):
    """Test context extraction."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    text = "This is a long piece of text. Contact John for more details. He is the expert."
    position = text.index("Contact John")
    
    context = agent._extract_context(text, position, 50)
    
    assert "Contact John" in context
    assert len(context) <= 60  # 50 + ellipsis


def test_is_code_file(sample_workspace):
    """Test code file detection."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    assert agent._is_code_file('src/main.py')
    assert agent._is_code_file('app.js')
    assert agent._is_code_file('service.java')
    assert not agent._is_code_file('README.md')
    assert not agent._is_code_file('data.json')


def test_get_security_mitigation(sample_workspace):
    """Test security mitigation advice."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    mitigation = agent._get_security_mitigation('hardcoded_password')
    assert 'environment' in mitigation.lower() or 'secrets' in mitigation.lower()
    
    mitigation = agent._get_security_mitigation('sql_injection')
    assert 'parameterized' in mitigation.lower() or 'orm' in mitigation.lower()


def test_analyze_risks_complete(
    sample_workspace,
    sample_repo_artifact,
    sample_db_artifact,
    sample_docs_artifact,
    sample_topology_artifact
):
    """Test complete risk analysis."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    result = agent.analyze_risks(
        sample_repo_artifact,
        sample_db_artifact,
        sample_docs_artifact,
        sample_topology_artifact
    )
    
    # Should return analysis artifact
    assert result.artifact_type == 'risk_register'
    assert result.engagement_id == config.engagement_id
    
    # Should have risks
    risks = result.data['risks']
    assert len(risks) > 0
    
    # Should have summary
    summary = result.data['summary']
    assert summary['total_risks'] > 0
    assert 'critical_count' in summary
    assert 'high_count' in summary
    assert 'by_category' in summary
    
    # Should save artifacts
    assert (workspace.artifacts / 'risk_register.json').exists()
    assert (workspace.artifacts / 'risk_register.md').exists()


def test_risk_categories(
    sample_workspace,
    sample_repo_artifact,
    sample_db_artifact,
    sample_docs_artifact,
    sample_topology_artifact
):
    """Test that various risk categories are detected."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    result = agent.analyze_risks(
        sample_repo_artifact,
        sample_db_artifact,
        sample_docs_artifact,
        sample_topology_artifact
    )
    
    risks = result.data['risks']
    categories = set(r['category'] for r in risks)
    
    # Should have multiple categories
    assert len(categories) >= 2
    
    # Check expected categories
    expected_categories = {'spof', 'security', 'tribal_knowledge', 'manual_ops'}
    assert categories & expected_categories  # At least some overlap


def test_markdown_generation(
    sample_workspace,
    sample_repo_artifact,
    sample_db_artifact,
    sample_docs_artifact,
    sample_topology_artifact
):
    """Test markdown report generation."""
    workspace, config = sample_workspace
    agent = RiskAnalysisAgent(workspace, config)
    
    result = agent.analyze_risks(
        sample_repo_artifact,
        sample_db_artifact,
        sample_docs_artifact,
        sample_topology_artifact
    )
    
    # Check markdown file
    md_path = workspace.artifacts / 'risk_register.md'
    assert md_path.exists()
    
    content = md_path.read_text()
    
    # Should have header
    assert '# Risk Analysis Report' in content
    
    # Should have summary
    assert 'Executive Summary' in content
    
    # Should have risks
    assert 'Risk Register' in content or 'No significant risks' in content