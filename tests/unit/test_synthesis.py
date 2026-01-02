"""Unit tests for SynthesisAgent."""

import pytest
from pathlib import Path
from datetime import datetime

from agents.synthesis import SynthesisAgent
from core.models import AnalysisArtifact, SourceReference, EngagementConfig
from skills.workspace import init_workspace, load_engagement_config


@pytest.fixture
def sample_workspace(tmp_path: Path):
    """Create sample workspace."""
    engagement_id = "test-synth-001"
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
    """Create sample topology artifact."""
    topology = {
        'statistics': {
            'total_nodes': 25,
            'total_edges': 48,
            'graph_density': 0.15,
            'avg_degree': 3.84,
        },
        'spofs': [
            {
                'node_name': 'database.py',
                'node_type': 'module',
                'risk_level': 'high',
                'centrality': 0.85,
                'dependent_components': ['user_service.py', 'order_service.py']
            }
        ]
    }
    
    return AnalysisArtifact(
        artifact_type='topology',
        engagement_id='test-synth-001',
        data=topology,
        sources=[],
        metrics={}
    )


@pytest.fixture
def sample_cost_artifact():
    """Create sample cost drivers artifact."""
    cost = {
        'cost_drivers': [
            {
                'table': 'users',
                'query_pattern': 'SELECT * FROM users WHERE email = ?',
                'execution_count': 1500,
                'avg_duration_ms': 145.5,
                'total_cost_ms': 218250.0,
                'impact': 'HIGH',
                'missing_indexes': ['email'],
                'recommendations': ['Consider adding index on users.email']
            },
            {
                'table': 'sessions',
                'query_pattern': 'SELECT id FROM sessions WHERE user_id = ?',
                'execution_count': 5000,
                'avg_duration_ms': 5.5,
                'total_cost_ms': 27500.0,
                'impact': 'MEDIUM',
                'missing_indexes': [],
                'recommendations': ['Query is already optimized']
            }
        ],
        'summary': {
            'total_queries_analyzed': 6500,
            'unique_query_patterns': 45,
            'total_cost_ms': 245750.0,
            'high_impact_count': 1,
            'medium_impact_count': 1,
            'low_impact_count': 0,
        }
    }
    
    return AnalysisArtifact(
        artifact_type='cost_drivers',
        engagement_id='test-synth-001',
        data=cost,
        sources=[],
        metrics={}
    )


@pytest.fixture
def sample_risk_artifact():
    """Create sample risk register artifact."""
    risk = {
        'risks': [
            {
                'title': 'Security: Hardcoded Password in config.py',
                'description': 'Found hardcoded password in configuration file',
                'severity': 'CRITICAL',
                'category': 'security',
                'confidence': 'high',
                'mitigation': 'Move credentials to environment variables'
            },
            {
                'title': 'SPOF: database.py',
                'description': 'Database module is a single point of failure',
                'severity': 'HIGH',
                'category': 'spof',
                'confidence': 'high',
                'mitigation': 'Implement database connection pooling'
            },
            {
                'title': 'Tribal Knowledge: John Smith',
                'description': 'John Smith mentioned 5 times as knowledge source',
                'severity': 'HIGH',
                'category': 'tribal_knowledge',
                'confidence': 'medium',
                'mitigation': 'Document expertise formally'
            }
        ],
        'summary': {
            'total_risks': 3,
            'critical_count': 1,
            'high_count': 2,
            'medium_count': 0,
            'low_count': 0,
            'by_category': {
                'security': 1,
                'spof': 1,
                'tribal_knowledge': 1
            }
        }
    }
    
    return AnalysisArtifact(
        artifact_type='risk_register',
        engagement_id='test-synth-001',
        data=risk,
        sources=[],
        metrics={}
    )


def test_synthesis_agent_initialization(sample_workspace):
    """Test SynthesisAgent can be initialized."""
    workspace, config = sample_workspace
    
    agent = SynthesisAgent(workspace, config)
    
    assert agent.workspace == workspace
    assert agent.config == config


def test_extract_metrics(
    sample_workspace,
    sample_topology_artifact,
    sample_cost_artifact,
    sample_risk_artifact
):
    """Test metric extraction."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    metrics = agent._extract_metrics(
        sample_topology_artifact,
        sample_cost_artifact,
        sample_risk_artifact
    )
    
    # Should extract key metrics
    assert 'total_components' in metrics
    assert 'total_dependencies' in metrics
    assert 'spof_count' in metrics
    assert 'total_cost_ms' in metrics
    assert 'total_risks' in metrics
    assert 'critical_risks' in metrics
    
    # Check values
    assert metrics['total_components'] == 25
    assert metrics['total_dependencies'] == 48
    assert metrics['spof_count'] == 1
    assert metrics['total_risks'] == 3
    assert metrics['critical_risks'] == 1


def test_identify_top_findings(
    sample_workspace,
    sample_cost_artifact,
    sample_risk_artifact
):
    """Test top findings identification."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    findings = agent._identify_top_findings(
        sample_cost_artifact,
        sample_risk_artifact
    )
    
    # Should have mix of cost and risk findings
    assert len(findings) > 0
    
    types = set(f['type'] for f in findings)
    assert 'cost' in types
    assert 'risk' in types
    
    # Check structure
    for finding in findings:
        assert 'type' in finding
        assert 'title' in finding
        assert 'description' in finding
        assert 'impact' in finding


def test_calculate_business_value(
    sample_workspace,
    sample_cost_artifact,
    sample_risk_artifact
):
    """Test business value calculation."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    value = agent._calculate_business_value(
        sample_cost_artifact,
        sample_risk_artifact
    )
    
    # Should calculate savings
    assert 'cost_savings_potential_ms' in value
    assert 'cost_savings_potential_hours_per_day' in value
    assert 'critical_risks_to_mitigate' in value
    
    # Check values are reasonable
    assert value['cost_savings_potential_ms'] > 0
    assert value['critical_risks_to_mitigate'] == 1


def test_prioritize_recommendations(
    sample_workspace,
    sample_cost_artifact,
    sample_risk_artifact
):
    """Test recommendation prioritization."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    recommendations = agent._prioritize_recommendations(
        sample_cost_artifact,
        sample_risk_artifact
    )
    
    # Should have recommendations
    assert len(recommendations) > 0
    
    # Check structure
    for rec in recommendations:
        assert 'priority' in rec
        assert 'category' in rec
        assert 'title' in rec
        assert 'description' in rec
        assert 'impact' in rec
        assert 'effort' in rec
    
    # Should be sorted by priority
    priorities = [r['priority'] for r in recommendations]
    assert priorities == sorted(priorities, reverse=True)


def test_calculate_priority(sample_workspace):
    """Test priority calculation."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    # CRITICAL risk should have highest priority
    critical_priority = agent._calculate_priority('risk', 'CRITICAL')
    high_priority = agent._calculate_priority('risk', 'HIGH')
    medium_priority = agent._calculate_priority('cost', 'MEDIUM')
    
    assert critical_priority > high_priority
    assert high_priority > medium_priority


def test_estimate_effort(sample_workspace):
    """Test effort estimation."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    # Security fix should be MEDIUM
    effort = agent._estimate_effort({'category': 'security'})
    assert effort == 'MEDIUM'
    
    # SPOF fix should be HIGH (architectural)
    effort = agent._estimate_effort({'category': 'spof'})
    assert effort == 'HIGH'
    
    # Documentation should be LOW
    effort = agent._estimate_effort({'category': 'documentation'})
    assert effort == 'LOW'


def test_format_findings_for_llm(sample_workspace):
    """Test findings formatting for LLM."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    findings = [
        {
            'impact': 'HIGH',
            'title': 'Cost Driver: users',
            'description': 'Query executing 1500 times'
        }
    ]
    
    formatted = agent._format_findings_for_llm(findings)
    
    assert 'HIGH' in formatted
    assert 'users' in formatted
    assert '1500' in formatted


def test_generate_template_executive_summary(
    sample_workspace,
    sample_topology_artifact,
    sample_cost_artifact,
    sample_risk_artifact
):
    """Test template-based executive summary generation."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    metrics = agent._extract_metrics(
        sample_topology_artifact,
        sample_cost_artifact,
        sample_risk_artifact
    )
    
    findings = agent._identify_top_findings(
        sample_cost_artifact,
        sample_risk_artifact
    )
    
    value = agent._calculate_business_value(
        sample_cost_artifact,
        sample_risk_artifact
    )
    
    recommendations = agent._prioritize_recommendations(
        sample_cost_artifact,
        sample_risk_artifact
    )
    
    summary = agent._generate_template_executive_summary(
        metrics,
        findings,
        value,
        recommendations
    )
    
    # Should have key sections
    assert '# Executive Summary' in summary
    assert 'Executive Overview' in summary
    assert 'Key Findings' in summary
    assert 'Business Impact' in summary
    assert 'Recommended Actions' in summary
    assert 'Next Steps' in summary
    
    # Should include client name
    assert config.client_name in summary


def test_generate_technical_appendix(
    sample_workspace,
    sample_topology_artifact,
    sample_cost_artifact,
    sample_risk_artifact
):
    """Test technical appendix generation."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    appendix = agent._generate_technical_appendix(
        sample_topology_artifact,
        sample_cost_artifact,
        sample_risk_artifact
    )
    
    # Should have key sections
    assert '# Technical Appendix' in appendix
    assert 'System Architecture Analysis' in appendix
    assert 'Performance & Cost Analysis' in appendix
    assert 'Risk Assessment' in appendix
    
    # Should include topology stats
    assert 'Total Components' in appendix or '25' in appendix
    
    # Should include cost drivers
    assert 'users' in appendix or 'Cost Drivers' in appendix
    
    # Should include risks
    assert 'CRITICAL' in appendix or 'HIGH' in appendix


def test_generate_action_plan(sample_workspace):
    """Test action plan generation."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    recommendations = [
        {
            'title': 'Add index on users.email',
            'impact': 'HIGH',
            'effort': 'LOW',
            'category': 'performance'
        },
        {
            'title': 'Implement SPOF mitigation',
            'impact': 'HIGH',
            'effort': 'HIGH',
            'category': 'availability'
        },
        {
            'title': 'Fix hardcoded password',
            'impact': 'CRITICAL',
            'effort': 'MEDIUM',
            'category': 'security'
        }
    ]
    
    plan = agent._generate_action_plan(recommendations)
    
    # Should have phased approach
    assert '# Action Plan' in plan
    assert 'Phase 1' in plan or 'Quick Wins' in plan
    
    # Should include success metrics
    assert 'Success Metrics' in plan or 'KPI' in plan


def test_generate_executive_summary_complete(
    sample_workspace,
    sample_topology_artifact,
    sample_cost_artifact,
    sample_risk_artifact
):
    """Test complete executive summary generation."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    result = agent.generate_executive_summary(
        sample_topology_artifact,
        sample_cost_artifact,
        sample_risk_artifact
    )
    
    # Should return artifact
    assert result.artifact_type == 'synthesis'
    assert result.engagement_id == config.engagement_id
    
    # Should have data
    data = result.data
    assert 'executive_summary' in data
    assert 'technical_appendix' in data
    assert 'action_plan' in data
    assert 'metrics' in data
    assert 'top_findings' in data
    assert 'business_value' in data
    assert 'recommendations' in data
    
    # Should have metrics
    assert result.metrics['total_findings'] > 0
    assert result.metrics['total_recommendations'] > 0
    
    # Should save artifacts
    assert (workspace.artifacts / 'synthesis.json').exists()
    assert (workspace.artifacts / 'executive_summary.md').exists()
    assert (workspace.artifacts / 'technical_appendix.md').exists()
    assert (workspace.artifacts / 'action_plan.md').exists()


def test_artifact_file_contents(
    sample_workspace,
    sample_topology_artifact,
    sample_cost_artifact,
    sample_risk_artifact
):
    """Test that generated files have proper content."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    agent.generate_executive_summary(
        sample_topology_artifact,
        sample_cost_artifact,
        sample_risk_artifact
    )
    
    # Check executive summary
    exec_path = workspace.artifacts / 'executive_summary.md'
    exec_content = exec_path.read_text()
    
    assert len(exec_content) > 500  # Should be substantial
    assert '# Executive Summary' in exec_content
    assert config.client_name in exec_content
    
    # Check technical appendix
    tech_path = workspace.artifacts / 'technical_appendix.md'
    tech_content = tech_path.read_text()
    
    assert len(tech_content) > 500
    assert '# Technical Appendix' in tech_content
    
    # Check action plan
    action_path = workspace.artifacts / 'action_plan.md'
    action_content = action_path.read_text()
    
    assert len(action_content) > 200
    assert '# Action Plan' in action_content


def test_synthesis_with_minimal_data(sample_workspace):
    """Test synthesis with minimal data."""
    workspace, config = sample_workspace
    agent = SynthesisAgent(workspace, config)
    
    # Create minimal artifacts
    topology = AnalysisArtifact(
        artifact_type='topology',
        engagement_id='test-synth-001',
        data={'statistics': {}, 'spofs': []},
        sources=[],
        metrics={}
    )
    
    cost = AnalysisArtifact(
        artifact_type='cost_drivers',
        engagement_id='test-synth-001',
        data={'cost_drivers': [], 'summary': {}},
        sources=[],
        metrics={}
    )
    
    risk = AnalysisArtifact(
        artifact_type='risk_register',
        engagement_id='test-synth-001',
        data={'risks': [], 'summary': {}},
        sources=[],
        metrics={}
    )
    
    # Should still generate summary
    result = agent.generate_executive_summary(topology, cost, risk)
    
    assert result.artifact_type == 'synthesis'
    assert 'executive_summary' in result.data